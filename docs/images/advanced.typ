#import "@preview/fletcher:0.5.8" as fletcher
#import "style.typ": *
#import "@preview/physica:0.9.8": *
#show: setup

#let node = fletcher.node
#let edge = fletcher.edge

= More Usage

#v(1em)

$
  cal(L)(matbold(x), vb(lambda), vb(mu)) &= sum_(i = 1)^n sum_(j =1)^m C_(i j) x_(i j) - sum_(i = 1)^n lambda_i (sum_(j=1)^m x_(i j) - s_i) - sum_(j = 1)^m mu_j (sum_(i=1)^n x_(i j) - d_j) \
  &= sum_(i=1)^n sum_(j =1)^m (C_(i j) - lambda_i - mu_j) x_(i j) + sum_(i=1)^n lambda_i s_i + sum_(j=1)^m mu_j d_j.
$

#v(1em)
$
                 "SL"_n (RR) & lt.closed.eq "GL"_n (RR) \
  "GL"_n (RR) \/ "SL"_n (RR) & tilde.equiv im det
$

#v(1em)

$
  A_(k n) = (2)/(J'_0(j_(0 k))^2) (2)/(L) integral_(0)^(1) integral_(0)^(L) f(rho, z) J_0 (j_(0 k) rho) sin((n ppi z)/(L)) rho dif z dif rho.
$


#v(1em)
#align(center)[
  #let el = muted
  #let elt(x) = text(fill: el, x)
  #fletcher.diagram(
    edge-stroke: ink + 0.6pt,
    node-stroke: none,
    spacing: (10em, 8.5em),
    // Elements on the outer corners; the spaces sit at fractional coordinates
    // between them, so the inner square stays centred whatever the labels.
    node((0, 0), elt($v$)),
    node((1, 0), elt($alpha(v)$)),
    node((0, 1), elt($[v]_B$)),
    node((1, 1), elt($[alpha]^B_C [v]_B = [alpha(v)]_C$)),
    edge((0, 0), (1, 0), elt($alpha$), "|->", stroke: el),
    edge((0, 0), (0, 1), elt($F_B$), "|->", stroke: el, label-side: right),
    edge((1, 0), (1, 1), elt($F_C$), "|->", stroke: el, label-side: left),
    edge((0, 1), (1, 1), elt($[alpha]^B_C$), "|->", stroke: el, label-side: right),
    node((0.2, 0.2), $V$, name: <V>),
    node((0.8, 0.2), $W$, name: <W>),
    node((0.2, 0.8), $FF^n$, name: <Fn>),
    node((0.8, 0.8), $FF^m$, name: <Fm>),
    edge(<V>, <W>, $alpha$, "->"),
    edge(<V>, <Fn>, $F_B$, "->", label-side: right),
    edge(<W>, <Fm>, $F_C$, "->", label-side: left),
    edge(<Fn>, <Fm>, $[alpha]^B_C$, "->", label-side: right),
  )
]
