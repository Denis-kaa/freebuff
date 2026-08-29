# Introduction

A `str` in Python is an [immutable sequence***REMOVED***[text sequence***REMOVED*** of [Unicode code points***REMOVED***[unicode code points***REMOVED***.
These could include letters, diacritical marks, positioning characters, numbers, currency symbols, emoji, punctuation, space and line break characters, and more.

Strings implement all [common sequence operations***REMOVED***[common sequence operations***REMOVED***, and can be iterated through using `for item in <string>` or `for index, item in enumerate(<string>)` syntax.

Strings can be concatenated with `<str> + <other str>` or `<str>.join(<iterable>)` and split via `<str>.split(<separator>)`.
They also offer multiple additional formatting, assembly, and templating options.

Being immutable, a `str` object's value in memory doesn't change; methods that appear to modify a string return a new copy or instance of `str`.

For a deep dive on what information a string encodes (or, _"how does a computer know how to translate zeroes and ones into letters?"_), [this blog post is enduringly helpful***REMOVED***[joel-on-text***REMOVED***.
The Python docs also provide a very detailed [unicode HOWTO***REMOVED***[unicode how-to***REMOVED*** that discusses Python's support for the Unicode specification in the `str`, `bytes` and `re` modules, considerations for locales, and some common issues with encoding and translation.


[common sequence operations***REMOVED***: https://docs.python.org/3/library/stdtypes.html#common-sequence-operations
[joel-on-text***REMOVED***: https://www.joelonsoftware.com/2003/10/08/the-absolute-minimum-every-software-developer-absolutely-positively-must-know-about-unicode-and-character-sets-no-excuses/
[text sequence***REMOVED***: https://docs.python.org/3/library/stdtypes.html#text-sequence-type-str
[unicode code points***REMOVED***: https://stackoverflow.com/questions/27331819/whats-the-difference-between-a-character-a-code-point-a-glyph-and-a-grapheme
[unicode how-to***REMOVED***: https://docs.python.org/3/howto/unicode.html
