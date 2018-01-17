# -*- coding:utf-8; python-indent:2; indent-tabs-mode:nil -*-

# Copyright 2013 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


"""Utilities for parsing pytd files for builtins."""

import collections


from pytype import utils
from pytype.pyi import parser
from pytype.pytd import pytd_utils
from pytype.pytd import visitors


def _FindBuiltinFile(name, python_version, extension=".pytd"):
  subdir = utils.get_versioned_path("builtins", python_version)
  _, src = pytd_utils.GetPredefinedFile(subdir, name, extension)
  return src


# Tests might run with different python versions in the same pytype invocation,
# so preserve the python version that was used to generate the cache.
# Cache: (version: tuple(int), cache: tuple(pytd.TypeDeclUnit))
Cache = collections.namedtuple("Cache", ("version", "cache"))
_cached_builtins_pytd = Cache(None, None)


def GetBuiltinsAndTyping(python_version):  # Deprecated. Use load_pytd instead.
  """Get __builtin__.pytd and typing.pytd."""
  assert python_version
  global _cached_builtins_pytd
  if _cached_builtins_pytd.cache:
    assert _cached_builtins_pytd.version == python_version
  else:
    t = parser.parse_string(_FindBuiltinFile("typing", python_version),
                            name="typing",
                            python_version=python_version)
    b = parser.parse_string(_FindBuiltinFile("__builtin__", python_version),
                            name="__builtin__",
                            python_version=python_version)
    b = b.Visit(visitors.LookupExternalTypes({"typing": t}, full_names=True,
                                             self_name="__builtin__"))
    t = t.Visit(visitors.LookupBuiltins(b))
    b = b.Visit(visitors.NamedTypeToClassType())
    t = t.Visit(visitors.NamedTypeToClassType())
    b = b.Visit(visitors.AdjustTypeParameters())
    t = t.Visit(visitors.AdjustTypeParameters())
    b = b.Visit(visitors.CanonicalOrderingVisitor())
    t = t.Visit(visitors.CanonicalOrderingVisitor())
    b.Visit(visitors.FillInLocalPointers({"": b, "typing": t,
                                          "__builtin__": b}))
    t.Visit(visitors.FillInLocalPointers({"": t, "typing": t,
                                          "__builtin__": b}))
    b.Visit(visitors.VerifyLookup())
    t.Visit(visitors.VerifyLookup())
    b.Visit(visitors.VerifyContainers())
    t.Visit(visitors.VerifyContainers())
    _cached_builtins_pytd = Cache(python_version, (b, t))
  return _cached_builtins_pytd.cache


def GetBuiltinsPyTD(python_version):  # Deprecated. Use Loader.concat_all.
  """Get the "default" AST used to lookup built in types.

  Get an AST for all Python builtins as well as the most commonly used standard
  libraries.

  Args:
    python_version: The python version tuple.
  Returns:
    A pytd.TypeDeclUnit instance. It'll directly contain the builtin classes
    and functions, and submodules for each of the standard library modules.
  """
  assert python_version
  return pytd_utils.Concat(*GetBuiltinsAndTyping(python_version))


# pyi for a catch-all module
DEFAULT_SRC = """
from typing import Any
def __getattr__(name: Any) -> Any: ...
"""


def GetDefaultAst(python_version):
  return parser.parse_string(src=DEFAULT_SRC, python_version=python_version)
