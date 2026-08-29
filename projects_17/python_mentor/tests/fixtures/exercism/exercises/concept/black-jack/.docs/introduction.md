# Introduction

## Comparisons

Python supports the following basic comparison operators:

| Operator | Operation                  | Description                                                               |
| -------- | -------------------------- | ------------------------------------------------------------------------- |
| `>`      | "greater than"             | `a > b` is `True` if `a` is **strictly** greater in value than `b`        |
| `<`      | "less than"                | `a < b` is `True` if `a` is **strictly** less in value than `b`           |
| `==`     | "equal to"                 | `a == b` is `True` if `a` is **strictly** equal to `b` in value           |
| `>=`     | "greater than or equal to" | `a >= b` is `True` if `a > b` OR `a == b` in value                        |
| `<=`     | "less than or equal to"    | `a <= b` is `True` if `a < b` or `a == b` in value                        |
| `!=`     | "not equal to"             | `a != b` is `True` if `a == b` is `False`                                 |
| `is`     | "identity"                 | `a is b` is `True` if **_and only if_** `a` and `b` are the same _object_ |
| `is not` | "negated identity"         | `a is not b` is `True` if `a` and `b` are **not** the same _object_       |
| `in`     | "containment test"         | `a in b` is `True` if `a` is member, subset, or element of `b`            |
| `not in` | "negated containment test" | `a not in b` is `True` if `a` is not a member, subset, or element of `b`  |

They all have the same priority (_which is higher than that of [Boolean operations***REMOVED***[boolean operations***REMOVED***, but lower than that of arithmetic or bitwise operations_).

## Comparison between different data types

Objects that are different types (_except numeric types_) never compare equal by default.
Non-identical instances of a `class` will also _**not**_ compare as equal unless the `class` defines special [rich comparison***REMOVED***[rich comparisons***REMOVED*** methods that customize the default `object` comparison behavior.
Customizing via `rich comparisons` will be covered in a follow-on exercise.
For (much) more detail on this topic, see [Value comparisons***REMOVED***[value comparisons***REMOVED*** in the Python documentation.

Numeric types are (mostly) an exception to this type matching rule.
An `integer` **can** be considered equal to a `float` (_or an [`octal`***REMOVED***[octal***REMOVED*** equal to a [`hexadecimal`***REMOVED***[hex***REMOVED***_), as long as the types can be implicitly converted for comparison.

For the other numeric types in the Python standard library ([complex***REMOVED***[complex numbers***REMOVED***, [decimal***REMOVED***[decimal numbers***REMOVED***, [fractions***REMOVED***[rational numbers***REMOVED***), comparison operators are defined where they "make sense" (_where implicit conversion does not change the outcome_), but throw a `TypeError` if the underlying objects cannot be accurately converted for comparison.
For more information on the rules that python uses for _numeric conversion_, see [arithmetic conversions***REMOVED***[arithmetic conversions***REMOVED*** in the Python documentation.

```python
>>> import fractions

# A string cannot be converted to an int.
>>> 17 == '17'
False

# An int can be converted to float for comparison.
>>> 17 == 17.0
True

# The fraction 6/3 can be converted to the int 2
# The int 2 can be converted to 0b10 in binary.
>>> 6/3 == 0b10
True

# An int can be converted to a complex number with a 0 imaginary part.
>>> 17 == complex(17)
True

# The fraction 2/5 can be converted to the float 0.4
>>> 0.4 == 2/5
True

>>> complex(2/5, 1/2) == complex(0.4, 0.5)
True
```

Any ordered comparison of a number to a `NaN` (_not a number_) type is `False`.
A confusing side effect of Python's `NaN` definition is that `NaN` never compares equal to `NaN`.

```python
>>> x = float('NaN')

>>> 3 < x
False

>>> x < 3
False

# NaN never compares equal to NaN
>>> x == x
False
```

## Comparing Strings

Unlike numbers, strings (`str`) are compared [_lexicographically_***REMOVED***[lexographic order***REMOVED***, using their individual Unicode code points (_the result of passing each code point in the `str` to the built-in function [`ord()`***REMOVED***[ord***REMOVED***, which returns an `int`_).
If all code points in both strings match and are _**in the same order**_, the two strings are considered equal.
This comparison is done in a 'pair-wise' fashion - first-to-first, second-to-second, etc.
In Python 3.x, `str` and `bytes` cannot be directly coerced/compared.

```python
>>> 'Python' > 'Rust'
False

>>> 'Python' > 'JavaScript'
True

# Examples with Mandarin.
# hello < goodbye
>>> '你好' < '再见'
True

# ord() of first characters
>>> ord('你'), ord('再')
(20320, 20877)

# ord() of second characters
>>> ord('好'), ord('见')
(22909, 35265)

# And with Korean words.
# Pretty < beautiful.
>>> '예쁜' < '아름다운'
False

>>> ord('예'), ord('아')
(50696, 50500)
```

## Comparison Chaining

Comparison operators can be chained _arbitrarily_ -- meaning that they can be used in any combination of any length.
Note that the evaluation of an expression takes place from `left` to `right`.

As an example, `x < y <= z` is equivalent to `x < y` `and` `y <= z`, except that `y` is evaluated **only once**.
In both cases, `z` is _not_ evaluated **at all** when `x < y` is found to be `False`.
This is often called `short-circuit evaluation` - the evaluation stops if the truth value of the expression has already been determined.

`Short circuiting` is supported by various boolean operators, functions, and also by comparison chaining in Python.
Unlike many other programming languages, including `C`, `C++`, `C#`, and `Java`, chained expressions like `a < b < c` in Python have a conventional [mathematical interpretation***REMOVED***[three way boolean comparison***REMOVED*** and precedence.

```python
>>> x = 2
>>> y = 5
>>> z = 10

>>> x < y < z
True

>>> x < y > z
False

>>> x > y < z
False
```

## Comparing object identity

The operators `is` and `is not` test for object [_identity_***REMOVED***[object identity***REMOVED***, as opposed to object _value_.
An object's identity never changes after creation and can be found by using the [`id()`***REMOVED***[id function***REMOVED*** function.

`<apple> is <orange>` evaluates to `True` if _**and only if**_ `id(<apple>)` == `id(<orange>)`.
`<apple> is not <orange>` yields the inverse.

Due to their singleton status, `None` and `NotImplemented` should always be compared to items using `is` and `is not`.
See the Python reference docs on [value comparisons***REMOVED***[value comparisons none***REMOVED*** and [PEP8***REMOVED***[pep8 programming recommendations***REMOVED*** for more details on this convention.

```python
>>> my_fav_numbers = [1, 2, 3***REMOVED***

>>> your_fav_numbers = my_fav_numbers

>>> my_fav_numbers is your_fav_numbers
True

# The returned id will differ by system and python version.
>>> id(my_fav_numbers)
4517478208

# your_fav_numbers is only an alias pointing to the original my_fav_numbers object.
# Assigning a new name does not create a new object.
>>> id(your_fav_numbers)
4517478208


>>> my_fav_numbers is not your_fav_numbers
False

>>> my_fav_numbers is not None
True

>>> my_fav_numbers is NotImplemented
False
```

## Membership comparisons

The operators `in` and `not in` test for _membership_.
`<fish> in <soup>` evaluates to `True` if `<fish>` is a member of `<soup>` (_if `<fish>` is a subset of or is contained within `<soup>`_), and evaluates `False` otherwise.
`<fish> not in <soup>` returns the negation, or _opposite of_ `<fish> in <soup>`.

For string and bytes types, `<name> in <fullname>` is `True` _**if and only if**_ `<name>` is a substring of `<fullname>`.

```python
# A set of lucky numbers.
>>> lucky_numbers = {11, 22, 33***REMOVED***
>>> 22 in lucky_numbers
True

>>> 44 in lucky_numbers
False

# A dictionary of employee information.
>>> employee = {'name': 'John Doe', 
                'id': 67826, 'age': 33, 
                'title': 'ceo'***REMOVED***

# Checking for the membership of certain keys.
>>> 'age' in employee
True

>>> 33 in employee
False

>>> 'lastname' not in employee
True

# Checking for substring membership
>>> name = 'Super Batman'
>>> 'Bat' in name
True

>>> 'Batwoman' in name
False
```

[arithmetic conversions***REMOVED***: https://docs.python.org/3/reference/expressions.html?highlight=number%20conversion#arithmetic-conversions
[boolean operations***REMOVED***: https://docs.python.org/3/library/stdtypes.html#boolean-operations-and-or-not
[complex numbers***REMOVED***: https://docs.python.org/3/library/functions.html#complex
[decimal numbers***REMOVED***: https://docs.python.org/3/library/decimal.html
[hex***REMOVED***: https://docs.python.org/3/library/functions.html?highlight=hex#hex
[id function***REMOVED***: https://docs.python.org/3/library/functions.html#id
[lexographic order***REMOVED***: https://en.wikipedia.org/wiki/Lexicographic_order
[object identity***REMOVED***: https://docs.python.org/3/reference/datamodel.html
[octal***REMOVED***: https://docs.python.org/3/library/functions.html?#oct
[ord***REMOVED***: https://docs.python.org/3/library/functions.html#ord
[pep8 programming recommendations***REMOVED***: https://pep8.org/#programming-recommendations
[rational numbers***REMOVED***: https://docs.python.org/3/library/fractions.html
[rich comparisons***REMOVED***: https://docs.python.org/3/reference/datamodel.html#object.__lt__
[three way boolean comparison***REMOVED***: https://en.wikipedia.org/wiki/Three-way_comparison
[value comparisons none***REMOVED***: https://docs.python.org/3/reference/expressions.html?highlight=none#value-comparisons
[value comparisons***REMOVED***: https://docs.python.org/3/reference/expressions.html?highlight=nan#value-comparisons
