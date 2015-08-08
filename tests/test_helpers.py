# -*- coding: utf-8 -*-
#
# test_helpers.py
#
# Copyright (C) 2011, 2013, 2015 Uli Fouquet
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
#
from __future__ import unicode_literals
import os
import shutil
import stat
import tempfile
import unittest
import zipfile
try:
    from cStringIO import StringIO  # Python 2.x
except ImportError:                 # pragma: no cover
    from io import StringIO         # Python 3.x
from ulif.openoffice.processor import OOConvProcessor
from ulif.openoffice.helpers import (
    copytree, copy_to_secure_location, get_entry_points, unzip, zip,
    remove_file_dir, extract_css, cleanup_html, cleanup_css,
    rename_html_img_links, rename_sdfield_tags, base64url_encode,
    base64url_decode, string_to_bool, strict_string_to_bool,
    string_to_stringtuple, filelike_cmp, write_filelike)


class TestHelpers(unittest.TestCase):

    def setUp(self):
        self.workdir = tempfile.mkdtemp()
        self.resultpath = None
        return

    def tearDown(self):
        shutil.rmtree(self.workdir)
        path = self.resultpath
        if isinstance(path, str):
            if os.path.isfile(path):
                path = os.path.dirname(path)
            shutil.rmtree(path)
        return

    def test_copytree_ignore(self):
        # we can pass a function to ignore files
        def ignore(src, names):
            return ['sample1.txt', ]
        self.resultpath = tempfile.mkdtemp()
        open(os.path.join(self.workdir, 'sample1.txt'), 'w').write('Hi!')
        open(os.path.join(self.workdir, 'sample2.txt'), 'w').write('Hi!')
        copytree(self.workdir, self.resultpath, ignore=ignore)
        assert not os.path.isfile(
            os.path.join(self.resultpath, 'sample1.txt'))
        assert os.path.isfile(
            os.path.join(self.resultpath, 'sample2.txt'))

    def test_copytree_subdirs(self):
        # subdirs are copies as well
        os.mkdir(os.path.join(self.workdir, 'srcdir'))
        os.mkdir(os.path.join(self.workdir, 'srcdir', 'sub1'))
        copytree(
            os.path.join(self.workdir, 'srcdir'),
            os.path.join(self.workdir, 'dstdir'))
        assert os.path.isdir(
            os.path.join(self.workdir, 'dstdir', 'sub1'))

    def test_copytree_links(self):
        # we copy links
        src_dir = os.path.join(self.workdir, 'srcdir')
        os.mkdir(src_dir)
        open(os.path.join(src_dir, 'sample.txt'), 'w').write('Hi!')
        os.symlink(
            os.path.join(src_dir, 'sample.txt'),
            os.path.join(src_dir, 'sample.link'))
        copytree(src_dir, os.path.join(self.workdir, 'dstdir'), symlinks=True)
        dst_link = os.path.join(self.workdir, 'dstdir', 'sample.link')
        assert os.path.islink(dst_link)
        assert os.readlink(dst_link) == os.path.join(src_dir, 'sample.txt')

    def test_copytree_ioerror(self):
        # we catch IOErrors, collect them and raise at end
        src_dir = os.path.join(self.workdir, 'srcdir')
        os.mkdir(src_dir)
        dst_dir = os.path.join(self.workdir, 'dstdir')
        os.mkdir(dst_dir)
        src_file = os.path.join(src_dir, 'sample1.txt')
        dst_file = os.path.join(dst_dir, 'sample1.txt')
        open(src_file, 'w').write('Hi!')
        open(dst_file, 'w').write('Ho!')

        # make dst_file unwriteable
        old_mode = os.stat(dst_file).st_mode
        os.chmod(dst_file, stat.S_IREAD)
        exc = None
        try:
            copytree(
                src_dir, dst_dir, symlinks=False)
        except (shutil.Error) as exc:
            exc = exc
        # reenable writing
        os.chmod(dst_file, old_mode)

        assert isinstance(exc, shutil.Error)
        assert len(exc.args) == 1
        err_src, err_dst, err_msg = exc.args[0][0]
        self.assertEqual(err_src, src_file)
        self.assertEqual(err_dst, dst_file)
        self.assertEqual(
            err_msg,
            u"[Errno 13] Permission denied: u'%s'" % dst_file)

    def test_copytree_shutil_error(self):
        # We catch shutil.Errors, collect them and raise at end
        # Also #1 regression
        src_dir = os.path.join(self.workdir, 'srcdir')
        os.mkdir(src_dir)
        src_file = os.path.join(src_dir, 'sample.txt')
        open(src_file, 'w').write('Hi!')
        # source and dest are the same. Provokes shutil.Error
        exc = None
        try:
            copytree(src_dir, src_dir)
        except (shutil.Error) as exc:
            exc = exc
        assert isinstance(exc, shutil.Error)
        assert len(exc.args) == 1
        err_src, err_dst, err_msg = exc.args[0][0]
        self.assertEqual(err_src, src_file)
        self.assertEqual(err_dst, src_file)
        self.assertEqual(
            err_msg,
            '`%s` and `%s` are the same file' % (src_file, src_file))

    def test_copy_to_secure_location_file(self):
        sample_path = os.path.join(self.workdir, 'sample.txt')
        open(sample_path, 'wb').write("Hi from sample")
        self.resultpath = copy_to_secure_location(sample_path)
        assert os.path.isfile(os.path.join(self.resultpath, 'sample.txt'))

    def test_copy_to_secure_location_path(self):
        sample_path = os.path.join(self.workdir, 'sample.txt')
        open(sample_path, 'wb').write("Hi from sample")
        sample_dir = os.path.dirname(sample_path)
        self.resultpath = copy_to_secure_location(sample_dir)
        assert os.path.isfile(os.path.join(self.resultpath, 'sample.txt'))

    def test_get_entry_points(self):
        result = get_entry_points('ulif.openoffice.processors')
        assert result['oocp'] is OOConvProcessor

    def test_unzip(self):
        # make sure we can unzip filetrees
        zip_file = os.path.join(self.workdir, 'sample.zip')
        shutil.copy(
            os.path.join(os.path.dirname(__file__), 'input', 'sample1.zip'),
            zip_file)
        dst = os.path.join(self.workdir, 'dst')
        os.mkdir(dst)
        unzip(zip_file, dst)
        assert os.listdir(dst) == ['somedir']
        level2_dir = os.path.join(dst, 'somedir')
        assert sorted(os.listdir(level2_dir)) == [
            'othersample.txt', 'sample.txt']

    def test_zip_file(self):
        # make sure we can zip single files
        new_dir = os.path.join(self.workdir, 'sampledir')
        os.mkdir(new_dir)
        sample_file = os.path.join(new_dir, 'sample.txt')
        open(sample_file, 'wb').write('A sample')
        self.resultpath = zip(sample_file)
        assert zipfile.is_zipfile(self.resultpath)

    def test_zip_dir(self):
        # make sure we can zip complete dir trees
        new_dir = os.path.join(self.workdir, 'sampledir')
        os.mkdir(new_dir)
        os.mkdir(os.path.join(new_dir, 'subdir1'))
        os.mkdir(os.path.join(new_dir, 'subdir2'))
        os.mkdir(os.path.join(new_dir, 'subdir2', 'subdir21'))
        sample_file = os.path.join(new_dir, 'subdir2', 'sample.txt')
        open(sample_file, 'wb').write('A sample')
        self.resultpath = zip(new_dir)
        zip_file = zipfile.ZipFile(self.resultpath, 'r')
        result = sorted(zip_file.namelist())
        assert sorted(result) == [
            'subdir1/', 'subdir2/', 'subdir2/sample.txt', 'subdir2/subdir21/']
        assert zip_file.testzip() is None

    def test_zip_invalid_path(self):
        # we get a ValueError if zip path is not valid
        self.assertRaises(
            ValueError, zip, 'not-a-valid-path')

    def test_remove_file_dir_none(self):
        assert remove_file_dir(None) is None

    def test_remove_file_dir_non_path(self):
        assert remove_file_dir(object()) is None

    def test_remove_file_dir_not_existiing(self):
        assert remove_file_dir('not-existing-path') is None

    def test_remove_file_dir_file(self):
        # When we remove a file, also the containung dir is removed
        sample_path = os.path.join(self.workdir, 'sampledir')
        sample_file = os.path.join(sample_path, 'sample.txt')
        os.mkdir(sample_path)
        open(sample_file, 'wb').write('Hi!')
        remove_file_dir(sample_file)
        assert os.path.exists(self.workdir) is True
        assert os.path.exists(sample_path) is False

    def test_remove_file_dir_dir(self):
        sample_path = os.path.join(self.workdir, 'sampledir')
        sample_file = os.path.join(sample_path, 'sample.txt')
        os.mkdir(sample_path)
        open(sample_file, 'wb').write('Hi!')
        remove_file_dir(sample_path)
        assert os.path.exists(self.workdir) is True
        assert os.path.exists(sample_path) is False

    def test_extract_css(self):
        """

        >> from ulif.openoffice.helpers import extract_css
        >> html, css = extract_css('''
        ... <!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
        ... "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
        ... <html xmlns="http://www.w3.org/1999/xhtml">
        ... <head>
        ... <meta name="generator" content="HTML Tidy for Linux/x86" />
        ... <meta http-equiv="CONTENT-TYPE" content="text/html;
        ...       charset=utf-8" />
        ...          <title>
        ...          </title>
        ...          <meta name="GENERATOR"
        ...                content="OpenOffice.org 2.4 (Linux)" />
        ...          <style type="text/css">
        ...           /* <![CDATA[ */
        ...            @page { size: 21cm 29.7cm; margin: 2cm }
        ...            p { margin-bottom: 0.21cm }
        ...            span.c2 {font-family: DejaVu Sans Mono, sans-serif}
        ...            p.c1 {margin-bottom: 0cm}
        ...           /* ]]> */
        ...          </style>
        ...         </head>
        ...         <body lang="de-DE" dir="ltr" xml:lang="de-DE">
        ...         </body>
        ...        </html>
        ... ''', 'sample.html')

      The returned css part contains all styles from input:

        >> print css
        @page { size: 21cm 29.7cm; margin: 2cm }
        p { margin-bottom: 0.21cm }
        span.c2 {font-family: DejaVu Sans Mono, sans-serif}
        p.c1 {margin-bottom: 0cm}

      The returned HTML part has the styles replaced with a link:

        >> print html # doctest: +ELLIPSIS, +NORMALIZE_WHITESPACE
        <!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
        "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
         <html xmlns="http://www.w3.org/1999/xhtml">
          <head>
           <meta name="generator" content="HTML Tidy for Linux/x86" />
           <meta http-equiv="CONTENT-TYPE" content="text/html;
               charset=utf-8" />
           <title>
           </title>
          <meta name="GENERATOR" content="OpenOffice.org 2.4 (Linux)" />
          <link rel="stylesheet" type="text/css" href="sample.css" />
         </head>
         <body lang="de-DE" dir="ltr" xml:lang="de-DE">
         </body>
        </html>

        """

    def test_extract_css_trash(self):
        # Also trashy docs can be handled
        result, css = extract_css("", 'sample.html')
        assert css is None
        assert result == ""

    def test_extract_css_simple(self):
        result, css = extract_css(
            "<style>a, b</style>", 'sample.html')
        link = '<link href="sample.css" rel="stylesheet" type="text/css"/>'
        assert css == 'a, b'
        assert result == link

    def test_extract_css_empty_styles1(self):
        # Also trashy docs can be handled
        result, css = extract_css(
            "<style></style>", 'sample.html')
        assert css is None
        assert result == ""

    def test_extract_css_empty_styles2(self):
        # Also trashy docs can be handled
        result, css = extract_css(
            "<html><style /></html>", 'sample.html')
        assert css is None
        assert result == "<html></html>"

    def test_extract_css_nested_styles(self):
        # Trash in, trash out...
        result, css = extract_css(
            "<html><style>a<style>b</style></style></html>", 'sample.html')
        assert css == 'a\nb'

    def test_extract_css_utf8(self):
        result, css = extract_css(
            "<html><body>äö</body></html>", 'sample.html')
        assert css is None
        assert result == '<html><body>äö</body></html>'

    def test_extract_css_utf8_unicode(self):
        result, css = extract_css(
            "<html><body>ä</body></html>", 'sample.html')
        assert css is None
        assert result == '<html><body>ä</body></html>'
        return

    def test_extract_css_complex_html(self):
        # Make sure we have styles purged and replaced by a link
        html_input_path = os.path.join(
            os.path.dirname(__file__), 'input', 'sample2.html')
        html_input = open(html_input_path, 'rb').read()
        result, css = extract_css(html_input, 'sample.html')
        assert '<style' not in result
        link = '<link href="sample.css" rel="stylesheet" type="text/css"/>'
        assert link in result
        return

    def test_extract_css_complex_css(self):
        # Make sure we get proper external stylesheets.
        html_input_path = os.path.join(
            os.path.dirname(__file__), 'input', 'sample2.html')
        html_input = open(html_input_path, 'rb').read()
        result, css = extract_css(html_input, 'sample.html')
        assert len(css) == 156
        assert css.startswith('@page { size: 21cm')
        return

    def test_extract_css_no_empty_comments(self):
        # Make sure there are no empty comments in CSS
        html_input_path = os.path.join(
            os.path.dirname(__file__), 'input', 'sample2.html')
        html_input = open(html_input_path, 'rb').read()
        result, css = extract_css(html_input, 'sample.html')
        assert '/*' not in result
        return

    def test_extract_css_prettify(self):
        # We can get prettified HTML (although it might be broken)
        result, css = extract_css(
            "<span>text<span>no</span>gap</span>", "sample.html",
            prettify_html=True
        )
        assert result == (
            "<span>\n text\n <span>\n  no\n </span>\n gap\n</span>"
            )

    def test_extract_css_no_prettify_by_default(self):
        # by default we do not get prettified html
        result, css = extract_css(
            "<span>text<span>no</span>gap</span>", "sample.html"
        )
        assert result == "<span>text<span>no</span>gap</span>"

    def test_cleanup_html_fix_img_links(self):
        html_input_path = os.path.join(
            os.path.dirname(__file__), 'input', 'image_sample.html')
        html_input = open(html_input_path, 'rb').read()
        result, img_map = cleanup_html(
            html_input, 'sample.html', fix_img_links=True)
        assert len(img_map) == 4

    def test_cleanup_html_fix_head_nums(self):
        html_input = '<body><h1>1.1Heading</h1></body>'
        result, img_map = cleanup_html(html_input, 'sample.html')
        expected = '<body><h1><span class="u-o-headnum">%s</span>'
        expected += 'Heading</h1></body>'
        assert result == expected % ('1.1')

    def test_cleanup_html_fix_head_nums_no_nums(self):
        html_input = '<body><h1>Heading</h1></body>'
        result, img_map = cleanup_html(html_input, 'sample.html')
        assert result == '<body><h1>Heading</h1></body>'

    def test_cleanup_html_fix_head_nums_trailing_dot(self):
        html_input = '<body><h1>1.1.Heading</h1></body>'
        result, img_map = cleanup_html(html_input, 'sample.html')
        expected = '<body><h1><span class="u-o-headnum">%s</span>'
        expected += 'Heading</h1></body>'
        assert result == expected % ('1.1.')

    def test_cleanup_html_fix_head_nums_h6(self):
        html_input = '<body><h6>1.1.Heading</h6></body>'
        result, img_map = cleanup_html(html_input, 'sample.html')
        expected = '<body><h6><span class="u-o-headnum">%s</span>'
        expected += 'Heading</h6></body>'
        assert result == expected % ('1.1.')

    def test_cleanup_html_fix_head_nums_tag_attrs(self):
        html_input = '<body><h6 class="foo">1.1.Heading</h6></body>'
        result, img_map = cleanup_html(html_input, 'sample.html')
        expected = '<body><h6 class="foo"><span class="u-o-headnum">%s'
        expected += '</span>Heading</h6></body>'
        assert result == expected % ('1.1.')

    def test_cleanup_html_fix_head_nums_linebreaks(self):
        html_input = '<body><h1>\n 1.1.Heading</h1></body>'
        result, img_map = cleanup_html(html_input, 'sample.html')
        expected = '<body><h1>\n <span class="u-o-headnum">%s</span>'
        expected += 'Heading</h1></body>'
        assert result == expected % ('1.1.')

    def test_cleanup_html_fix_sdfields(self):
        html_input = '<p>Blah<sdfield type="PAGE">8</sdfield></p>'
        result, img_map = cleanup_html(html_input, 'sample.html')
        expected = '<p>Blah<span class="sdfield" type="PAGE">8</span></p>'
        assert result == expected

    def test_cleanup_html_dont_fix_sdfields(self):
        html_input = '<p>Blah<sdfield type="PAGE">8</sdfield></p>'
        result, img_map = cleanup_html(html_input, 'sample.html',
                                       fix_sdfields=False)
        assert html_input == result

    def test_cleanup_html_no_minify_by_default(self):
        # by default, cleanup_html does not minify code
        html_input = '<span>\n<span>foo</span>\n</span>'
        result, img_map = cleanup_html(html_input, 'sample.html')
        assert result == html_input

    def test_rename_sdfield_tags(self):
        html_input = '<p>Blah<sdfield type="PAGE">8</sdfield></p>'
        result = rename_sdfield_tags(html_input)
        expected = b'<p>Blah<span class="sdfield" type="PAGE">8</span></p>'
        assert result == expected

    def test_rename_sdfield_tags_uppercase(self):
        html_input = '<P>Blah<SDFIELD TYPE="PAGE">8</SDFIELD></P>'
        result = rename_sdfield_tags(html_input)
        expected = b'<P>Blah<span class="sdfield" TYPE="PAGE">8</span></P>'
        assert result == expected

    def test_rename_sdfield_tags_empty(self):
        html_input = '<p>Blah</p>'
        result = rename_sdfield_tags(html_input)
        expected = b'<p>Blah</p>'
        assert result == expected

    def test_rename_sdfield_tags_nested(self):
        html_input = '<p>Blah<sdfield>12<span>b</span></sdfield></p>'
        result = rename_sdfield_tags(html_input)
        expected = b'<p>Blah<span class="sdfield">12<span>b</span></span></p>'
        assert result == expected

    def test_cleanup_css_whitespace(self):
        css_input = 'p {font-family: ; font-size: 12px }'
        result, errors = cleanup_css(css_input)
        assert result == b'p{font-size:12px}'

    def test_cleanup_css_empty_style(self):
        css_input = 'p {}'
        result, errors = cleanup_css(css_input)
        assert result == b''

    def test_cleanup_css_empty_prop(self):
        css_input = 'p {font-family: ;}'
        result, errors = cleanup_css(css_input)
        assert result == b''

    def test_cleanup_css_empty_prop_no_colon(self):
        css_input = 'p {font-family: }'
        result, errors = cleanup_css(css_input)
        assert result == b''

    def test_cleanup_css_empty_prop_middle(self):
        css_input = 'p { foo: baz ; font-family: ; bar: baz}'
        result, errors = cleanup_css(css_input)
        assert result == b'p{foo:baz;bar:baz}'

    def test_cleanup_css_complex(self):
        css_sample = os.path.join(
            os.path.dirname(__file__), 'input', 'sample1.css')
        css_input = open(css_sample, 'rb').read()
        result, errors = cleanup_css(css_input)
        assert b'font-family: ;' not in result

    def test_cleanup_css_errors(self):
        css_input = 'p { foo: baz ; font-family: ; bar: baz}'
        result, errors = cleanup_css(css_input)
        assert 'ERROR PropertyValue: Unknown syntax' in errors
        assert 'WARNING Property: Unknown Property name' in errors

    def test_cleanup_css_non_minified(self):
        css_input = 'p { foo: baz ; bar: baz}'
        result, errors = cleanup_css(css_input, minified=False)
        assert result == b'p {\n    foo: baz;\n    bar: baz\n    }'

    def test_rename_html_img_links(self):
        # Make sure img links are modified
        html_input_path = os.path.join(
            os.path.dirname(__file__), 'input', 'image_sample.html')
        html_input = open(html_input_path, 'rb').read()
        html_output, img_map = rename_html_img_links(html_input, 'sample.html')
        assert 'image_sample_html_10a8ad02.jpg' not in html_output
        assert 'sample_4.jpg' in html_output
        assert len(img_map.keys()) == 4  # 4 images are in doc
        assert 'image_sample_html_10a8ad02.jpg' in img_map.keys()
        assert 'sample_4.jpg' in img_map.values()

    def test_rename_html_img_links_no_ext(self):
        html_input = '<img src="filename_without_ext" />'
        html_output, img_map = rename_html_img_links(html_input, 'sample.html')
        assert html_output == '<img src="sample_1"/>'
        assert img_map == {'filename_without_ext': 'sample_1'}

    def test_rename_html_img_links_unicode_filenames(self):
        html_input = '<img src="filename_without_ext" />'
        html_output, img_map = rename_html_img_links(html_input, 'sample.html')
        key = img_map.keys()[0]
        val = img_map.values()[0]
        assert isinstance(key, unicode)
        assert isinstance(val, unicode)

    def test_rename_html_img_links_only_local(self):
        # We do not convert links to external images
        html_input = '<img src="http://sample/image.gif" />'
        html_output, img_map = rename_html_img_links(html_input, 'sample.html')
        assert len(img_map.keys()) == 0
        assert 'http://sample/image.gif' in html_output

    def test_rename_html_img_links_umlauts(self):
        # We can handle umlauts in filenames
        html_input = '<img src="file with ümlaut.gif" />'
        html_output, img_map = rename_html_img_links(html_input, 'sample.html')
        assert img_map == {'file with \xfcmlaut.gif': 'sample_1.gif'}

    def test_rename_html_img_links_multiple_img(self):
        # Check that multiple links to same file get same target
        html_input = (
            '<img src="a.gif" /><img src="a.gif"' + '/><img src="b.gif" />')
        html_output, img_map = rename_html_img_links(
            html_input, 'sample.html')
        assert img_map == {
            'a.gif': 'sample_1.gif',
            'b.gif': 'sample_2.gif'}
        assert html_output == '%s%s' % (
            '<img src="sample_1.gif"/><img src="sample_1.gif"/>',
            '<img src="sample_2.gif"/>')

    def test_rename_html_img_links_ignore_img_without_src(self):
        # we ignore img tags that have no 'src' attribute
        html_input = ('<img name="foo" /><img name="bar" src="baz" />')
        html_output, img_map = rename_html_img_links(
            html_input, 'sample.html')
        assert img_map == {'baz': 'sample_1'}
        assert html_output == (
            '<img name="foo"/>'
            '<img name="bar" src="sample_1"/>')

    def test_base64url_encode(self):
        assert base64url_encode(chr(251) + chr(239)) == '--8='
        assert base64url_encode(chr(255) * 2) == '__8='
        assert base64url_encode("foo") == "Zm9v"
        assert base64url_encode(b"foo") == "Zm9v"
        assert base64url_encode(u"foo") == "Zm9v"

    def test_base64url_decode(self):
        exp1 = chr(251) + chr(239)
        assert base64url_decode(b'--8=') == exp1
        exp2 = chr(255) * 2
        assert base64url_decode(b'__8=') == exp2

    def test_string_to_bool(self):
        assert string_to_bool('yes') is True
        assert string_to_bool('1') is True
        assert string_to_bool('tRuE') is True
        assert string_to_bool('nO') is False
        assert string_to_bool('0') is False
        assert string_to_bool('FaLsE') is False
        assert string_to_bool(True) is True
        assert string_to_bool(False) is False
        assert string_to_bool('nonsense') is None
        assert string_to_bool(object()) is None

    def test_strict_string_to_bool(self):
        assert strict_string_to_bool('yes') is True
        assert strict_string_to_bool('no') is False
        self.assertRaises(ValueError, strict_string_to_bool, 'nonsense')

    def test_string_to_stringtuple(self):
        assert string_to_stringtuple('foo') == ('foo', )
        assert string_to_stringtuple('foo, bar') == ('foo', 'bar')
        assert string_to_stringtuple('foo,bar') == ('foo', 'bar')
        assert string_to_stringtuple(' foo ') == ('foo', )
        assert string_to_stringtuple('') == ()
        assert string_to_stringtuple('foo,,,bar') == ('foo', 'bar')
        assert string_to_stringtuple(None) == ()
        assert string_to_stringtuple(',,,,') == ()
        # with `strict` empty strings are forbidden
        self.assertRaises(
            ValueError, string_to_stringtuple, '', strict=True)
        self.assertRaises(
            ValueError, string_to_stringtuple, None, strict=True)

    def test_filelike_cmp(self):
        assert filelike_cmp(
            StringIO(b'asd'), StringIO(b'qwe')) is False
        assert filelike_cmp(
            StringIO(b'asd'), StringIO(b'asd')) is True
        p1 = os.path.join(self.workdir, b'p1')
        p2 = os.path.join(self.workdir, b'p2')
        p3 = os.path.join(self.workdir, b'p3')
        with open(p1, 'w') as fd:
            fd.write(b'asd')
        with open(p2, 'w') as fd:
            fd.write(b'qwe')
        with open(p3, 'w') as fd:
            fd.write(b'asd')
        assert filelike_cmp(p1, p2) is False
        assert filelike_cmp(p1, p3) is True
        assert filelike_cmp(p1, StringIO(b'asd')) is True
        assert filelike_cmp(StringIO(b'qwe'), p2) is True

    def test_filelike_cmp_multiple_time(self):
        # make sure filepointers are reset when we use the same
        # file-like object several times (as often happens in loops).
        p1 = os.path.join(self.workdir, b'p1')
        with open(p1, 'w') as fd:
            fd.write(b'foo')
        filelike1 = StringIO(b'foo')
        filelike2 = StringIO(b'bar')
        assert filelike_cmp(p1, filelike1) is True
        assert filelike_cmp(p1, filelike2) is False
        assert filelike_cmp(p1, filelike1) is True
        assert filelike_cmp(p1, filelike2) is False

    def test_write_filelike(self):
        src = os.path.join(self.workdir, b'f1')
        with open(src, 'w') as fd:
            fd.write(b'content')
        dst = os.path.join(self.workdir, b'f2')
        write_filelike(open(src, 'rb'), dst)
        assert open(dst, 'rb').read() == b'content'
        write_filelike(b'different', dst)
        assert open(dst, 'rb').read() == b'different'
