"""
A simple unicode palette for greek lettering.

Most useful as a one liner: >>> from recipes import greek
"""

alphabet = """\
    Standard
    --------
    α β γ δ ε ζ η θ ι κ λ μ ν ξ ο π ρ ς σ τ υ φ χ ψ ω
    Α Β Γ Δ Ε Ζ Η Θ Ι Κ Λ Μ Ν Ξ Ο Π Ρ   Σ Τ Υ Φ Χ Ψ Ω
    
    ϕ 𝜙
     
    Special
    -------
    𝜓 ∇ ∂ 𝟅 𝟆 𝟇 𝟈 𝟉
"""
# TODO: bold? bb bold?
# FIXME: ∂ - SyntaxError: invalid character in identifier
print(alphabet, flush=True)