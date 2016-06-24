#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This code implements a basic, Twitter-aware tokenizer.

A tokenizer is a function that splits a string of text into words. In
Python terms, we map string and unicode objects into lists of unicode
objects.

There is not a single right way to do tokenizing. The best method
depends on the application.  This tokenizer is designed to be flexible
and this easy to adapt to new domains and tasks.  The basic logic is
this:

1. The tuple regex_strings defines a list of regular expression
   strings.

2. The regex_strings strings are put, in order, into a compiled
   regular expression object called word_re.

3. The tokenization is done by word_re.findall(s), where s is the
   user-supplied string, inside the tokenize() method of the class
   Tokenizer.

4. When instantiating Tokenizer objects, there is a single option:
   preserve_case.  By default, it is set to True. If it is set to
   False, then the tokenizer will downcase everything except for
   emoticons.


"""

__author__ = "Christopher Potts"
__copyright__ = "Copyright 2011, Christopher Potts"
__credits__ = []
__license__ = "Creative Commons Attribution-NonCommercial-ShareAlike 3.0 Unported License: http://creativecommons.org/licenses/by-nc-sa/3.0/"
__version__ = "1.0"
__maintainer__ = "Christopher Potts"
__email__ = "See the author's website"

######################################################################

import re
import htmlentitydefs

######################################################################
# The following strings are components in the regular expression
# that is used for tokenizing. It's important that phone_number
# appears first in the final regex (since it can contain whitespace).
# It also could matter that tags comes after emoticons, due to the
# possibility of having text like
#
#     <:| and some text >:)
#
# Most imporatantly, the final element should always be last, since it
# does a last ditch whitespace-based tokenization of whatever is left.

# This particular element is used in a couple ways, so we define it
# with a name:
emoticon_string = r"""
    (?:
      [<>]?
      [:;=8]                     # eyes
      [\-o\*\']?                 # optional nose
      [\)\]\(\[dDpP/\:\}\{@\|\\] # mouth
      |
      [\)\]\(\[dDpP/\:\}\{@\|\\] # mouth
      [\-o\*\']?                 # optional nose
      [:;=8]                     # eyes
      [<>]?
    )"""

# The components of the tokenizer:
regex_strings = (
    # Phone numbers:
    r"""
    (?:
      (?:            # (international)
        \+?[01]
        [\-\s.]*
      )?
      (?:            # (area code)
        [\(]?
        \d{3}
        [\-\s.\)]*
      )?
      \d{3}          # exchange
      [\-\s.]*
      \d{4}          # base
    )"""
    ,
    # Emoticons:
    emoticon_string
    ,
    # HTML tags:
     r"""<[^>]+>"""
    ,
    # Twitter username:
    r"""(?:@[\w_]+)"""
    ,
    # Twitter hashtags:
    r"""(?:\#+[\w_]+[\w\'_\-]*[\w_]+)"""
    ,
    # Remaining word types:
    r"""
    (?:[a-z][a-z'\-_]+[a-z])       # Words with apostrophes or dashes.
    |
    (?:[+\-]?\d+[,/.:-]\d+[+\-]?)  # Numbers, including fractions, decimals.
    |
    (?:[\w_]+)                     # Words without apostrophes or dashes.
    |
    (?:\.(?:\s*\.){1,})            # Ellipsis dots.
    |
    (?:\S)                         # Everything else that isn't whitespace.
    """
    )

######################################################################
# This is the core tokenizing regex:

word_re = re.compile(r"""(%s)""" % "|".join(regex_strings), re.VERBOSE | re.I | re.UNICODE)

# The emoticon string gets its own regex so that we can preserve case for them as needed:
emoticon_re = re.compile(regex_strings[1], re.VERBOSE | re.I | re.UNICODE)

# These are for regularizing HTML entities to Unicode:
html_entity_digit_re = re.compile(r"&#\d+;")
html_entity_alpha_re = re.compile(r"&\w+;")
amp = "&amp;"

######################################################################

class PottsTokenizer(object):
    def __init__(self, preserve_case=False):
        self.preserve_case = preserve_case

    def tokenize(self, s):
        """
        Argument: s -- any string or unicode object
        Value: a tokenize list of strings; conatenating this list returns the original string if preserve_case=False
        """
        # Try to ensure unicode:
        try:
            s = unicode(s)
        except UnicodeDecodeError:
            s = str(s).encode('string_escape')
            s = unicode(s)
        # Tokenize:
        words = word_re.findall(s)
        # Possible alter the case, but avoid changing emoticons like :D into :d:
        if not self.preserve_case:
            words = map((lambda x : x if emoticon_re.search(x) else x.lower()), words)
        return words


###############################################################################

class MyPottsTokenizer(PottsTokenizer):
    """
    Class to improve potts tokenizer to handle
    NoneTypes.
    """


    def tokenize(self, s):
        """
        Override the PottsTokenizer 'tokenize'
        method to ensure it better handles
        incorrect types
        """

        if isinstance(s, str):
            return super(MyPottsTokenizer, self).tokenize(s)
        else:
            raise TypeError, "Tokenizer got %s, expected str" % type(s)



class NegationSuffixAdder():
    """
    Class to add simple negation marking to tokenized
    text to aid in sentiment analysis.

    A good explanation of negation marking, along with
    details of the approach used here can be found at:

    http://sentiment.christopherpotts.net/lingstruc.html#negation

    As defined in the link above, the basic approach is to
    "Append a _NEG suffix to every word appearing between a
    negation and a clause-level punctuation mark". Here, negation
    words are defined as those that match the NEGATION_RE regex, and
    clause-level punctuation marks are those that match the PUNCT_RE regex.

    Please note that this method is due to Das & Chen (2001) and
    Pang, Lee & Vaithyanathan (2002)

    """

    # Regex credit: Chris Potts

    # regex to match negation tokens
    NEGATION_RE = re.compile("""(?x)(?:
    ^(?:never|no|nothing|nowhere|noone|none|not|
        havent|hasnt|hadnt|cant|couldnt|shouldnt|
        wont|wouldnt|dont|doesnt|didnt|isnt|arent|aint
     )$
    )
    |
    n't""")

    # regex to match punctuation tokens
    PUNCT_RE = re.compile("^[.:;!?]$")

    def __init__(self):
        pass

    def add_negation_suffixes(self, tokens):
        """
        INPUT: List of strings (tokenized sentence)
        OUTPUT: List of string with negation suffixes added

        Adds negation markings to a tokenized string.
        """

        # negation tokenization
        neg_tokens = []
        append_neg = False # stores whether to add "_NEG"

        for token in tokens:

            # if we see clause-level punctuation,
            # stop appending suffix
            if self.PUNCT_RE.match(token):
                append_neg = False

            # Do or do not append suffix, depending
            # on state of 'append_neg'
            if append_neg:
                neg_tokens.append(token + "_NEG")
            else:
                neg_tokens.append(token)

            # if we see negation word,
            # start appending suffix
            if self.NEGATION_RE.match(token):
                append_neg = True

        return neg_tokens
