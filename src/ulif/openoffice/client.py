##
## client.py
##
## Copyright (C) 2013 Uli Fouquet
## This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.
##
## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
##
"""
Client API to access all functionality via programmatic calls.
"""
import os
from ulif.openoffice.cachemanager2 import CacheManager, get_marker
from ulif.openoffice.helpers import copy_to_secure_location
from ulif.openoffice.processor import MetaProcessor


def convert_doc(src_doc, options, cache_dir):
    """Convert `src_doc` according to the other parameters.

    `src_doc` is the path to the source document. `options` is a dict
    of options for processing, passed to the processors.

    `cache_dir` may be ``None`` in which no caching is requested
    during processing.

    Generates a converted representation of `src_doc` by calling
    :class:`ulif.openoffice.processor.MetaProcessor` with `options` as
    parameters.

    Afterwards the conversion result is stored in cache (if
    allowed/possible) for speedup of upcoming requests.

    Returns a triple:

      ``(<PATH>, <CACHE_KEY>, <METADATA>)``

    where ``<PATH>`` is the path to the resulting document,
    ``<CACHE_KEY>`` an identifier (string) to retrieve a generated doc
    from cache on future requests, and ``<METADATA>`` is a dict of values
    returned during request (and set by the document processors,
    notably setting the `error` keyword).

    If errors happen or caching is disabled, ``<CACHE_KEY>`` is
    ``None``.
    """
    result_path = None
    cache_key = None
    repr_key = get_marker(options)  # Create unique marker out of options
    metadata = dict(error=False)

    # Generate result
    input_copy = src_doc
    if cache_dir:
        input_copy = copy_to_secure_location(src_doc)
        input_copy = os.path.join(input_copy, os.path.basename(src_doc))
    proc = MetaProcessor(options=options)  # Removes original doc
    result_path, metadata = proc.process(input_copy)

    error_state = metadata.get('error', False)
    if cache_dir and not error_state and result_path is not None:
        # Cache away generated doc
        cache_key = CacheManager(cache_dir).register_doc(
            src_doc, result_path, repr_key)
    return result_path, cache_key, metadata
