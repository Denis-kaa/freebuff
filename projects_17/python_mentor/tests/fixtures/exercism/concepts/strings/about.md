# About

A `str` in Python is an [immutable sequence***REMOVED***[text sequence***REMOVED*** of [Unicode code points***REMOVED***[unicode code points***REMOVED***.
These may include letters, diacritical marks, positioning characters, numbers, currency symbols, emoji, punctuation, space and line break characters, and more.

For a deep dive on what information a string encodes (or, _"how does a computer know how to translate zeroes and ones into letters?"_), [this blog post is enduringly helpful***REMOVED***[joel-on-text***REMOVED***.
The Python docs also provide a very detailed [unicode HOWTO***REMOVED***[unicode how-to***REMOVED*** that discusses Python's support for the Unicode specification in the `str`, `bytes` and `re` modules, considerations for locales, and some common issues with encoding and translation.

Strings implement all [common sequence operations***REMOVED***[common sequence operations***REMOVED*** and can be iterated through using `for item in <str>` or `for index, item in enumerate(<str>)` syntax.
 Individual code points (_strings of length 1_) can be referenced by `0-based index` number from the left, or `-1-based index` number from the right.

Strings can be concatenated with `<str> + <other str>` or `<str>.join(<iterable>)` and split via `<str>.split(<separator>)`.
They also offer multiple additional formatting, assembly, and templating options.


A `str` literal can be declared using single `'` or double `"` quotes. The escape `\` character is available as needed.

```python

>>> single_quoted = 'These allow "double quoting" without "escape" characters.'

>>> double_quoted = "These allow embedded 'single quoting', so you don't have to use an 'escape' character."
```


Multi-line strings are declared with `'''` or `"""`.

```python
>>> triple_quoted = '''Three single quotes or "double quotes" in a row allow for multi-line string literals.
  Line break characters, tabs and other whitespace is fully supported. Remember - The escape "\" character is also available if needed (as can be seen below). 
  
  You\'ll most often encounter multi-line strings as "doc strings" or "doc tests" written just below the first line of a function or class definition.
    They\'re often used with auto documentation ✍ tools.
    '''
```

The [`str(<object>)` constructor***REMOVED***[str-constructor***REMOVED*** can be used to create/coerce strings from other objects:

```python
>>> my_number = 42
>>> str(my_number)
...
"42"
```

While the `str(<object>)` constructor can be used to coerce/convert strings, it _**will not iterate**_ or unpack an object.
This is different from the behavior of constructors for other data types such as `list()`, `set()`, `dict()`, or `tuple()`, and can have surprising results.


```python
>>> numbers = [1,3,5,7***REMOVED***
>>> str(numbers)
...
'[1,3,5,7***REMOVED***'
```


Code points within a `str` can be referenced by `0-based index` number from the left:

```python
creative = '창의적인'

>>> creative[0***REMOVED***
'창'

>>> creative[2***REMOVED***
'적'

>>> creative[3***REMOVED***
'인'

```

Indexing also works from the right, starting with a `-1-based index`:

```python
creative = '창의적인'

>>> creative[-4***REMOVED***
'창'

>>> creative[-2***REMOVED***
'적'

>>> creative[-1***REMOVED***
'인'

```

There is no separate “character” or "rune" type in Python, so indexing a string produces a new `str` of **length 1**:

```python

>>> website = "exercism"
>>> type(website[0***REMOVED***)
<class 'str'>

>>> len(website[0***REMOVED***)
1

>>> website[0***REMOVED*** == website[0:1***REMOVED*** == 'e'
True
```

Substrings can be selected via _slice notation_, using [`<str>[<start>:<stop>:<step>***REMOVED***`***REMOVED***[common sequence operations***REMOVED*** to produce a new string.
Results exclude the `stop` index.
If no `start` is given, the starting index will be 0.
If no `stop` is given, the `stop` index will be the end of the string.


```python
moon_and_stars = '🌟🌟🌙🌟🌟⭐'

>>> moon_and_stars[1:4***REMOVED***
'🌟🌙🌟'

>>> moon_and_stars[:3***REMOVED***
'🌟🌟🌙'

>>> moon_and_stars[3:***REMOVED***
'🌟🌟⭐'

>>> moon_and_stars[:-1***REMOVED***
'🌟🌟🌙🌟🌟'

>>> moon_and_stars[:-3***REMOVED***
'🌟🌟🌙'
```

Strings can also be broken into smaller strings via [`<str>.split(<separator>)`***REMOVED***[str-split***REMOVED***, which will return a `list` of substrings.
Using `<str>.split()` without any arguments will split the string on whitespace.


```python
>>> cat_ipsum = "Destroy house in 5 seconds command the hooman."
>>> cat_ipsum.split()
...
['Destroy', 'house', 'in', '5', 'seconds', 'command', 'the', 'hooman.'***REMOVED***


>>> cat_words = "feline, four-footed, ferocious, furry"
>>> cat_words.split(',')
...
['feline', ' four-footed', ' ferocious', ' furry'***REMOVED***


>>> colors = """red,
orange,
green,
purple,
yellow"""

>>> colors.split(',\n')
['red', 'orange', 'green', 'purple', 'yellow'***REMOVED***
```

Strings can be concatenated using the `+` operator.
This method should be used sparingly, as it is not very performant or easily maintained.

```python
language = "Ukrainian"
number = "nine"
word = "дев'ять"

sentence = word + " " + "means" + " " + number + " in " + language + "."

>>> print(sentence)
...
"дев'ять means nine in Ukrainian."
```

If a `list`, `tuple`, `set` or other collection of individual strings needs to be combined into a single `str`, [`<str>.join(<iterable>)`***REMOVED***[str-join***REMOVED*** is a better option:


```python
# str.join() makes a new string from the iterables elements.
>>> chickens = ["hen", "egg", "rooster"***REMOVED*** # Lists are iterable.
>>> ' '.join(chickens)
'hen egg rooster'

# Any string can be used as the joining element.
>>> ' :: '.join(chickens)
'hen :: egg :: rooster'

>>> ' 🌿 '.join(chickens)
'hen 🌿 egg 🌿 rooster'


# Any iterable can be used as input.
>>> flowers = ("rose", "daisy", "carnation")  # Tuples are iterable.
>>> '*-*'.join(flowers)
'rose*-*daisy*-*carnation'

>>> flowers = {"rose", "daisy", "carnation"***REMOVED***  # Sets are iterable, but output order is not guaranteed.
>>> '*-*'.join(flowers)
'rose*-*carnation*-*daisy'

>>> phrase = "This is my string"  # Strings are iterable, but be careful!
>>> '..'.join(phrase)
'T..h..i..s.. ..i..s.. ..m..y.. ..s..t..r..i..n..g'


# Separators are inserted **between** elements, but can be any string (including spaces).
# This can be exploited for interesting effects.
>>> under_words = ['under', 'current', 'sea', 'pin', 'dog', 'lay'***REMOVED***
>>> separator = ' ⤴️ under' # Note the leading space, but no trailing space.
>>> separator.join(under_words)
'under ⤴️ undercurrent ⤴️ undersea ⤴️ underpin ⤴️ underdog ⤴️ underlay'

# The separator can be composed different ways, as long as the result is a string.
>>> upper_words = ['upper', 'crust', 'case', 'classmen', 'most', 'cut'***REMOVED***
>>> separator = ' 🌟 ' + upper_words[0***REMOVED*** # This becomes one string, similar to ' ⤴️ under'.
>>> separator.join(upper_words)
 'upper 🌟 uppercrust 🌟 uppercase 🌟 upperclassmen 🌟 uppermost 🌟 uppercut'
```

Strings support all [common sequence operations***REMOVED***[common sequence operations***REMOVED***.
Individual code points can be iterated through in a loop via `for item in <str>`.
Indexes _with_ items can be iterated through in a loop via `for index, item in enumerate(<str>)`.


```python

>>> exercise = 'လေ့ကျင့်'

# Note that there are more code points than perceived glyphs or characters.
# Care should be used when iterating over languages that use
# combining characters, or when dealing with emoji.
>>> for code_point in exercise:
...    print(code_point)
...
လ
ေ
့
က
ျ
င
်
့

# Using enumerate will give both the value and index position of each element.
>>> for index, code_point in enumerate(exercise):
...    print(index, ": ", code_point)
...
0 :  လ
1 :  ေ
2 :  ့
3 :  က
4 :  ျ
5 :  င
6 :  ်
7 :  ့
```


## String Methods

Python provides a rich set of [string methods***REMOVED***[str-methods***REMOVED*** that can assist with searching, cleaning, splitting, transforming, translating, and many other operations.
A selection of these methods are covered in another exercise.


## Formatting

Python also provides a rich set of tools for [formatting***REMOVED***[str-formatting***REMOVED*** and [templating***REMOVED***[template-strings***REMOVED*** strings, as well as more sophisticated text processing through the [re (_regular expressions_)***REMOVED***[re***REMOVED***, [difflib (_sequence comparison_)***REMOVED***[difflib***REMOVED***, and [textwrap***REMOVED***[textwrap***REMOVED*** modules.
For a great introduction to string formatting in Python, see [this post at Real Python***REMOVED***[real python string formatting***REMOVED***.
 For an introduction to string methods, see [Strings and Character Data in Python***REMOVED***[strings and characters***REMOVED*** at the same site.


## Related types and encodings

In addition to `str` (a _text_ sequence), Python has corresponding [binary sequence types***REMOVED***[binary sequence types***REMOVED*** summarized under [binary data services***REMOVED***[binary data services***REMOVED*** -- `bytes` (a _binary_ sequence), `bytearray`, and `memoryview` for the efficient storage and handling of binary data.
Additionally, [Streams***REMOVED***[streams***REMOVED*** allow sending and receiving binary data over a network connection without using callbacks.


[binary data services***REMOVED***: https://docs.python.org/3/library/binary.html#binaryservices
[binary sequence types***REMOVED***: https://docs.python.org/3/library/stdtypes.html#binaryseq
[common sequence operations***REMOVED***: https://docs.python.org/3/library/stdtypes.html#common-sequence-operations
[difflib***REMOVED***: https://docs.python.org/3/library/difflib.html
[joel-on-text***REMOVED***: https://www.joelonsoftware.com/2003/10/08/the-absolute-minimum-every-software-developer-absolutely-positively-must-know-about-unicode-and-character-sets-no-excuses/
[re***REMOVED***: https://docs.python.org/3/library/re.html
[real python string formatting***REMOVED***: https://realpython.com/python-string-formatting/
[str-constructor***REMOVED***: https://docs.python.org/3/library/stdtypes.html#str
[str-formatting***REMOVED***: https://docs.python.org/3/library/string.html#custom-string-formatting
[str-join***REMOVED***: https://docs.python.org/3/library/stdtypes.html#str.join
[str-methods***REMOVED***: https://docs.python.org/3/library/stdtypes.html#string-methods
[str-split***REMOVED***: https://docs.python.org/3/library/stdtypes.html#str.split
[streams***REMOVED***: https://docs.python.org/3/library/asyncio-stream.html#streams
[strings and characters***REMOVED***: https://realpython.com/python-strings/
[template-strings***REMOVED***: https://docs.python.org/3/library/string.html#template-strings
[text sequence***REMOVED***: https://docs.python.org/3/library/stdtypes.html#text-sequence-type-str
[textwrap***REMOVED***: https://docs.python.org/3/library/textwrap.html
[unicode code points***REMOVED***: https://stackoverflow.com/questions/27331819/whats-the-difference-between-a-character-a-code-point-a-glyph-and-a-grapheme
[unicode how-to***REMOVED***: https://docs.python.org/3/howto/unicode.html
