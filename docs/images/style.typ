// Shared look for the README images. Render them with scripts/render_samples.sh.

#let theme = sys.inputs.at("theme", default: "light")
#assert(theme in ("light", "dark"), message: "theme must be light or dark, got " + theme)

#let ink = luma(10%)
#let muted = luma(50%)
#let hairline = luma(80%)
#let background = luma(100%)

#if theme == "dark" {
  ink = luma(92.5%)
  muted = luma(50%)
  hairline = luma(25%)
  background = luma(10%)
}

#let setup(width: 16cm, body) = {
  set page(width: width, height: auto, margin: (x: 1cm, y: 1cm), fill: background)
  set text(font: "IBM Plex Sans", size: 11pt, fill: ink)
  set par(leading: 0.7em)
  show math.equation: set text(font: "Micfong Sans Math")
  body
}

#let label(body) = text(size: 9pt, fill: muted, body)
#let matbold(content) = math.upright(math.bold(content))
#let re = math.op("Re")
#let ppi = $upright(pi)$
#let ii = $upright(i)$
#let ee = $upright(e)$