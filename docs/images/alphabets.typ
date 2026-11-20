#import "style.typ": *
#show: setup

#let lower = "abcdefghijklmnopqrstuvwxyz"
#let upper = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
#let greek-lower = "αβγδεζηθικλμνξοπρστυφχψω"
#let greek-upper = "ΓΔΘΛΞΠΣΦΨΩ"
#let row(name, body) = (label(name), body)
#let each(s, style) = s.clusters().map(c => math.equation(style(c))).join()

#{
  set text(size: 12.5pt)
  grid(
    columns: (2.6cm, 1fr),
    column-gutter: 0.4cm,
    row-gutter: 0.75em,
    align: (right + horizon, left + horizon),
    ..row([Italic], [#each(lower, math.italic) \ #each(upper, math.italic)]),
    ..row([Upright], [#each(lower, math.upright) \ #each(upper, math.upright)]),
    ..row([Bold], [#each(lower, c => math.bold(math.upright(c)))]),
    ..row([Bold italic], [#each(lower, c => math.bold(math.italic(c)))]),
    ..row([Monospace], [#each(lower, math.mono) #h(0.5em) #each("0123456789", math.mono)]),
    ..row([Greek], [#each(greek-lower, math.italic) \ #each(greek-upper, math.upright) #h(0.5em) $theta.alt phi.alt epsilon.alt$]),
    ..row([Digits], [#each("0123456789", math.upright) #h(0.5em) #each("0123456789", c => math.bold(math.upright(c)))]),
    ..row([Cyrillic], $upright("АБВГДЕЖЗИКЛМНОПРСТУФХЦЧШЩЭЮЯ")$),
  )
}

#v(0.5em)
#line(length: 100%, stroke: 0.5pt + hairline)
#v(0.3em)

#{
  set text(size: 12.5pt)
  grid(
    columns: (2.6cm, 1fr),
    column-gutter: 0.4cm,
    row-gutter: 0.75em,
    align: (right + horizon, left + horizon),
    ..row([From LSM], $cal(A B C D E F G H) quad frak(A B C a b c) quad bb(N Z Q R C) quad kappa.alt rho.alt pi.alt quad aleph ell partial nabla$),
    ..row([], $sum product integral.cont sqrt(x) quad <= >= != approx prop quad arrow.r => arrow.r.bar quad in subset.eq union inter quad forall exists$),
  )
}
