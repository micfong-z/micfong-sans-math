#import "style.typ": *
#show: setup

// Each language is set in its IBM Plex family, with Latin from IBM Plex Sans.
#let sample(name, fonts, lang, region: none, body) = (
  align(right, label(name)),
  {
    set text(font: ("IBM Plex Sans", ..fonts), lang: lang, region: region)
    body
  },
)

= Multilingual Samples

#label("Paired with IBM Plex Sans font series")


#v(1em)

#grid(
  columns: (1.9cm, 1fr),
  column-gutter: 0.6cm,
  row-gutter: 1.05em,
  align: (right + top, left + top),
  ..sample("English", (), "en")[
    The Fourier transform of $f in L^1(RR)$ is
    $hat(f)(xi) = integral_RR f(x) e^(-2 pi i x xi) dif x$.
  ],
  ..sample("简体中文", ("IBM Plex Sans SC",), "zh", region: "cn")[
    设 $f$ 在 $[a, b]$ 上连续，$F' = f$，则 $integral_a^b f(x) dif x = F(b) - F(a)$.
  ],
  ..sample("繁體中文", ("IBM Plex Sans TC",), "zh", region: "tw")[
    若 $|q| < 1$，則幾何級數 $sum_(n=0)^infinity q^n = 1 / (1 - q)$ 收斂.
  ],
  ..sample("日本語", ("IBM Plex Sans JP",), "ja")[
    オイラーの等式 $e^(i pi) + 1 = 0$ は五つの基本定数を結ぶ。
  ],
  ..sample("한국어", ("IBM Plex Sans KR",), "ko")[
    직각삼각형에서는 $a^2 + b^2 = c^2$이 성립한다. 여기서 $c$는 빗변의 길이이다.
  ],
  ..sample("Русский", (), "ru")[
    Неравенство Коши — Буняковского: $|chevron.l u, v chevron.r| <= norm(u) norm(v)$.
  ],
  ..sample("Ελληνικά", (), "el")[
    Το εμβαδόν κυκλικού δίσκου ακτίνας $rho$ είναι $E = pi rho^2$.
  ],
  ..sample("हिन्दी", ("IBM Plex Sans Devanagari",), "hi")[
    द्विघात समीकरण $a x^2 + b x + c = 0$ के मूल $x = (-b plus.minus sqrt(b^2 - 4 a c)) / (2 a)$ होते हैं।
  ],
)
