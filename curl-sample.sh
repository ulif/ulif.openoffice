#!/bin/sh

# Sample post using curl. Here 'sample.doc' is the local document
# we want to convert.
curl -v -u bird:bebop --form "doc=@sample.doc" \
     http://localhost:8000/docs # > result.zip
