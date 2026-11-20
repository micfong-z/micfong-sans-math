// Micfong Sans Math in a Typst document, with IBM Plex for the text.
// From the repository root: typst compile --font-path dist samples/sample.typ
// The section in other scripts needs IBM Plex Sans SC, TC, JP, KR and Devanagari.

#set document(title: "Micfong Sans Math sample")
#set page(paper: "a4", margin: (x: 2.3cm, y: 2.4cm), numbering: "1")
#set text(font: "IBM Plex Sans", size: 10.5pt, lang: "en")
#set par(justify: true, leading: 0.68em)
#set heading(numbering: "1.")
#show heading: set text(weight: "semibold")
#show heading: set block(above: 1.6em, below: 0.9em)
#show raw: set text(font: "IBM Plex Mono", size: 9pt)
#let matbold(content) = math.upright(math.bold(content))
#let re = math.op("Re")
#let ppi = $upright(pi)$
#let ii = $upright(i)$
#let ee = $upright(e)$

// The one line that matters:
#show math.equation: set text(font: "Micfong Sans Math")
#set math.equation(numbering: "(1)")

#align(center)[
  #text(size: 20pt, weight: "semibold")[Micfong Sans Math]
]
#v(0.6em)

The equations in this document are set in Micfong Sans Math, a new open-source font for mathematics. The font is designed to be compatible with IBM Plex Sans, which is used for the body text.

To use Micfong Sans Math in your own Typst documents, install the font and add the following line to your document:
```typst
#show math.equation: set text(font: "Micfong Sans Math")
```

= Fourier series

Let $f: RR -> CC$ be $2 ppi$-periodic and integrable on $[-ppi, ppi]$. Its Fourier coefficients are
$ hat(f)(n) = 1 / (2 ppi) integral_(-ppi)^ppi f(x) ee^(-ii n x) dif x, quad n in ZZ, $ <coefficients>
and Parseval's identity states that
$ sum_(n in ZZ) |hat(f)(n)|^2 = 1 / (2 ppi) integral_(-ppi)^ppi |f(x)|^2 dif x. $ <parseval>
For $f(x) = x$ the coefficients are $hat(f)(0) = 0$ and $hat(f)(n) = (-1)^n ii slash n$, so @parseval gives $2 sum_(n >= 1) 1 slash n^2 = ppi^2 slash 3$, which is Euler's $zeta(2) = ppi^2 slash 6$.

= Linear algebra

A real symmetric matrix $matbold(A) in RR^(n times n)$ has an orthonormal basis of eigenvectors, so $matbold(A) = matbold(Q) matbold(Lambda) matbold(Q)^top$ with $matbold(Q)^top matbold(Q) = matbold(I)$ and $matbold(Lambda) = op("diag")(lambda_1, dots, lambda_n)$. For example,
$
  mat(2, 1; 1, 2) = 1 / 2 mat(1, -1; 1, 1) mat(1, 0; 0, 3) mat(1, 1; -1, 1), quad det(matbold(A) - lambda matbold(I)) = (lambda - 1)(lambda - 3).
$
The Rayleigh quotient $R(bold(x)) = (bold(x)^top matbold(A) bold(x)) slash (bold(x)^top bold(x))$ takes values in $[lambda_"min", lambda_"max"]$.

= Probability

A random variable $X tilde.op "N"(mu, sigma^2)$ has density
$ phi(x) = 1 / (sigma sqrt(2 ppi)) exp(-(x - mu)^2 / (2 sigma^2)), $
with $EE[X] = mu$ and $op("Var")(X) = sigma^2$. Whatever the distribution, as long as the variance is finite, Chebyshev's inequality bounds the tails:
$ PP(|X - mu| >= k sigma) <= 1 / k^2, quad k > 0. $

= Physics

Maxwell's equations in a vacuum:
$
  nabla dot bold(E) &= rho / epsilon_0, & quad nabla times bold(E) &= -(partial bold(B)) / (partial t), \
  nabla dot bold(B) &= 0, & quad nabla times bold(B) &= mu_0 bold(J) + mu_0 epsilon_0 (partial bold(E)) / (partial t).
$
The time-dependent Schrödinger equation is $ii ℏ thin partial_t Psi(bold(r), t) = hat(H) Psi(bold(r), t)$ with $hat(H) = -ℏ^2 / (2 m) nabla^2 + V(bold(r))$.

= Multilingual support

#let sample(name, fonts, lang, region: none, body) = {
  set text(font: ("IBM Plex Sans", ..fonts), lang: lang, region: region)
  set math.equation(numbering: none)
  grid(
    columns: (2.2cm, 1fr),
    column-gutter: 0.5cm,
    text(size: 8.5pt, fill: luma(100), name), body,
  )
  v(0.4em)
}

#sample("简体中文", ("IBM Plex Sans SC",), "zh", region: "cn")[
  设 $f$ 在区间 $[a, b]$ 上连续，且 $F' = f$，则
  $ integral_a^b f(x) dif x = F(b) - F(a). $
  这就是微积分基本定理。
]
#sample("繁體中文", ("IBM Plex Sans TC",), "zh", region: "tw")[
  若 $|q| < 1$，則幾何級數 $sum_(n=0)^infinity q^n$ 收斂，且其和為 $1 slash (1 - q)$。
]
#sample("日本語", ("IBM Plex Sans JP",), "ja")[
  オイラーの公式 $ee^(ii theta) = cos theta + ii sin theta$ において $theta = ppi$ とおくと、オイラーの等式 #box($ee^(ii ppi) + 1 = 0$) が得られる。
]
#sample("한국어", ("IBM Plex Sans KR",), "ko")[
  직각삼각형에서 빗변의 길이를 $c$, 나머지 두 변의 길이를 $a$, $b$라고 하면 $a^2 + b^2 = c^2$이 성립한다.
]
#sample("Русский", (), "ru")[
  Для любого $epsilon > 0$ существует $delta > 0$ такое, что $|f(x) - f(a)| < epsilon$ для всех $x$, удовлетворяющих $|x - a| < delta$. Тогда говорят, что функция $f$ непрерывна в точке $a$.
]
#sample("Ελληνικά", (), "el")[
  Το εμβαδόν κυκλικού δίσκου ακτίνας $rho$ είναι $E = ppi rho^2$, ενώ το μήκος του κύκλου είναι $L = 2 ppi rho$.
]
#sample("हिन्दी", ("IBM Plex Sans Devanagari",), "hi")[
  द्विघात समीकरण $a x^2 + b x + c = 0$, जहाँ $a != 0$, के मूल
  $ x = (-b plus.minus sqrt(b^2 - 4 a c)) / (2 a) $
  होते हैं।
]
