# Vertical (airmass-1) optical depths per absorber for the OCO bands at 0.01 cm^-1,
# US Standard Atmosphere 1976 (T, p), RH-50% troposphere for H2O, XCO2 = 420 ppm,
# O2 0.20946, CH4 1.9 ppm. CO2/O2/H2O from ABSCO v5.2 (ABSCO-only policy);
# CH4 line-by-line from the HITRAN .par artifact (no ABSCO CH4 table on disk).
using Pkg; Pkg.activate("/home/cfranken/code/gitHub/Google-RT"; io=devnull)
using AtmosphericAbsorption, NCDatasets, DelimitedFiles, Printf
const AA = AtmosphericAbsorption
const OUT = ARGS[1]
# ---- US Standard Atmosphere 1976 -----------------------------------------------
const g0 = 9.80665; const R = 8.31432; const M = 0.0289644; const p0 = 101325.0
const hb = [0.0, 11.0, 20.0, 32.0, 47.0, 51.0, 71.0, 84.852] .* 1e3   # m (geopotential)
const Tb = [288.15, 216.65, 216.65, 228.65, 270.65, 270.65, 214.65, 186.946]
const Lb = [-6.5, 0.0, 1.0, 2.8, 0.0, -2.8, -2.0] .* 1e-3            # K/m
function ussa(h)
    p = p0
    for i in 1:7
        htop = hb[i+1]
        if h <= htop
            L = Lb[i]; T = Tb[i] + L*(h - hb[i])
            pp = L == 0 ? p*exp(-g0*M*(h-hb[i])/(R*Tb[i])) : p*(Tb[i]/T)^(g0*M/(R*L))
            return (T, pp)
        end
        L = Lb[i]; Tt = Tb[i+1]
        p = L == 0 ? p*exp(-g0*M*(htop-hb[i])/(R*Tb[i])) : p*(Tb[i]/Tt)^(g0*M/(R*L))
    end
    return (Tb[end], p)
end
# invert p -> h by bisection (monotone)
function h_of_p(pt)
    lo, hi = 0.0, 84.8e3
    for _ in 1:80; mid = (lo+hi)/2; ussa(mid)[2] > pt ? (lo = mid) : (hi = mid); end
    return (lo+hi)/2
end
esat(T) = 611.2*exp(17.62*(T-273.15)/(T-30.03))       # Pa, Magnus over water
function h2o_vmr(T, p)  # RH 50 % in the troposphere, 4 ppm floor above
    e = 0.5*esat(T); v = e/(p - e); return max(min(v, 0.03), 4e-6)
end
# ---- layers: 60 log-spaced pressure edges 1013.25 hPa -> 0.05 hPa ---------------
p_edge = exp.(range(log(101325.0), log(5.0); length=61))          # Pa, BOA -> TOA
NA = 6.02214076e23
nlay = length(p_edge)-1
p_mid = zeros(nlay); T_mid = zeros(nlay); vh2o = zeros(nlay); Ndry = zeros(nlay)  # molec/cm^2 dry air
for i in 1:nlay
    pm = sqrt(p_edge[i]*p_edge[i+1]); T, _ = ussa(h_of_p(pm))
    v = h2o_vmr(T, pm); q_dry = v*(18.015/28.9644)          # kg H2O / kg dry
    dp = p_edge[i]-p_edge[i+1]
    m_moist = dp/g0                                        # kg/m^2 total
    m_dry = m_moist/(1 + q_dry)
    Ndry[i] = m_dry/M*NA*1e-4; p_mid[i] = pm/100; T_mid[i] = T; vh2o[i] = v
end
col_h2o_kgm2 = sum(Ndry .* vh2o) * 18.015e-3/NA * 1e4
@printf("atmosphere: %d layers, surface %.2f hPa, T_sfc %.2f K, H2O column %.2f kg m-2 (%.2f g cm-2)\n",
        nlay, p_edge[1]/100, ussa(0.0)[1], col_h2o_kgm2, col_h2o_kgm2/10)
# ---- bands ---------------------------------------------------------------------
const ABSCO = "/home/cfranken/data/ABSCO/v5.2_final"
bands = Dict(
  :aband => (12950.0, 13200.0, :o2),   # 757.6-772.2 nm
  :wco2  => (6165.0, 6295.0, :wco2),   # 1588.6-1622.1 nm
  :sco2  => (4800.0, 4900.0, :sco2))   # 2040.8-2083.3 nm
const CH4_PAR = "/home/cfranken/.julia/artifacts/d62e9581682e7b509e6b634e88600746ae37ed67/hitran_molec_id_6_CH4.par"
function column_tau(model, grid, vmr_gas; broad = false, lbl_vmr = false)
    τ = zeros(length(grid))
    for i in 1:nlay
        σ = broad ? AA.compute_cross_section(model, grid, p_mid[i], T_mid[i]; vmr = vh2o[i], interp = :linear) :
            lbl_vmr ? AA.compute_cross_section(model, grid, p_mid[i], T_mid[i]; vmr = vmr_gas[i]) :
                      AA.compute_cross_section(model, grid, p_mid[i], T_mid[i])
        τ .+= Float64.(Array(σ)) .* vmr_gas[i] .* Ndry[i]
    end
    return τ
end
for (name, (ν0, ν1, absband)) in bands
    grid = collect(ν0:0.01:ν1)
    @printf("\n== %s  %.2f-%.2f cm-1  (%d points)\n", name, ν0, ν1, length(grid))
    t = time()
    lut_h2o = AA.read_oco2_absco(joinpath(ABSCO, "h2o_v52.hdf"), absband; FT = Float64)
    τ_h2o = column_tau(lut_h2o, grid, vh2o; lbl_vmr = true)        # self-broadening via own vmr axis
    if absband == :o2
        lut = AA.read_oco2_absco(joinpath(ABSCO, "o2_v52.hdf"), absband; FT = Float64)
        τ_o2 = column_tau(lut, grid, fill(0.20946, nlay); broad = true); τ_co2 = zeros(length(grid))
    else
        lut = AA.read_oco2_absco(joinpath(ABSCO, "co2_v52.hdf"), absband; FT = Float64)
        τ_co2 = column_tau(lut, grid, fill(420e-6, nlay); broad = true); τ_o2 = zeros(length(grid))
    end
    cols = Any[grid, τ_co2, τ_o2, τ_h2o]; hdr = "nu_cm-1 tau_co2 tau_o2 tau_h2o"
    if name == :sco2
        lines = AA.load_lines(AA.HitranPort(CH4_PAR); mol = 6, ν_min = ν0 - 50, ν_max = ν1 + 50)
        mdl = AA.LineByLineModel(lines; wing_cutoff = 40)
        τ_ch4 = column_tau(mdl, grid, fill(1.9e-6, nlay))
        push!(cols, τ_ch4); hdr *= " tau_ch4"
        @printf("CH4: %d lines\n", length(lines))
    end
    @printf("tau max: co2 %.3g o2 %.3g h2o %.3g   (%.0f s)\n", maximum(τ_co2), maximum(τ_o2), maximum(τ_h2o), time()-t)
    open(joinpath(OUT, "tau_$(name)_lbl.txt"), "w") do io
        println(io, "# ", hdr); writedlm(io, hcat(cols...))
    end
end
println("DONE")
