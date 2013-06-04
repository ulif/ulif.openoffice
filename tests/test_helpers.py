# -*- coding: utf-8 -*-
##
## test_helpers.py
## Login : <uli@pu.smp.net>
## Started on  Mon May  2 00:53:37 2011 Uli Fouquet
## $Id$
## 
## Copyright (C) 2011 Uli Fouquet
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
import os
import shutil
import tempfile
import unittest
import zipfile
from ulif.openoffice.processor import OOConvProcessor
from ulif.openoffice.helpers import (
    copy_to_secure_location, get_entry_points, unzip, zip, remove_file_dir,
    extract_css, cleanup_html, cleanup_css, rename_html_img_links,
    rename_sdfield_tags, base64url_encode, base64url_decode, string_to_bool)

class TestHelpers(unittest.TestCase):

    def setUp(self):
        self.workdir = tempfile.mkdtemp()
        self.resultpath = None
        return

    def tearDown(self):
        shutil.rmtree(self.workdir)
        path = self.resultpath
        if isinstance(path, basestring):
            if os.path.isfile(path):
                path = os.path.dirname(path)
            shutil.rmtree(path)
        return

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
        zipfile = os.path.join(self.workdir, 'sample.zip')
        shutil.copy(
            os.path.join(os.path.dirname(__file__), 'input', 'sample1.zip'),
            zipfile)
        dst = os.path.join(self.workdir, 'dst')
        os.mkdir(dst)
        unzip(zipfile, dst)
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
        >> html, css = extract_css(u'''
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
        link = '<link rel="stylesheet" type="text/css" '
        link += 'href="sample.css" />\n'
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
        assert result == "<html>\n</html>"

    def test_extract_css_nested_styles(self):
        # Trash in, trash out...
        result, css = extract_css(
            "<html><style>a<style>b</style></style></html>", 'sample.html')
        assert css == u'a\nb'

    def test_extract_css_utf8(self):
        result, css = extract_css(
            "<html><body>äö</body></html>", 'sample.html')
        assert css is None
        assert result == '<html>\n <body>\n  äö\n </body>\n</html>'

    def test_extract_css_utf8_unicode(self):
        result, css = extract_css(
            u"<html><body>ä</body></html>", 'sample.html')
        assert css is None
        assert result == '<html>\n <body>\n  ä\n </body>\n</html>'
        return

    def test_extract_css_complex_html(self):
        # Make sure we have styles purged and replaced by a link
        html_input_path = os.path.join(
            os.path.dirname(__file__), 'input', 'sample2.html')
        html_input = open(html_input_path, 'rb').read()
        result, css = extract_css(html_input, 'sample.html')
        assert '<style' not in result
        link = '<link rel="stylesheet" type="text/css" href="sample.css" />'
        assert link in result
        return

    def test_extract_css_complex_css(self):
        # Make sure we get proper external stylesheets.
        html_input_path = os.path.join(
            os.path.dirname(__file__), 'input', 'sample2.html')
        html_input = open(html_input_path, 'rb').read()
        result, css = extract_css(html_input, 'sample.html')
        assert len(css) == 150
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

    def test_rename_sdfield_tags(self):
        html_input = '<p>Blah<sdfield type="PAGE">8</sdfield></p>'
        result = rename_sdfield_tags(html_input)
        expected = '<p>Blah<span class="sdfield" type="PAGE">8</span></p>'
        assert result == expected

    def test_rename_sdfield_tags_uppercase(self):
        html_input = '<P>Blah<SDFIELD TYPE="PAGE">8</SDFIELD></P>'
        result = rename_sdfield_tags(html_input)
        expected = '<P>Blah<span class="sdfield" TYPE="PAGE">8</span></P>'
        assert result == expected

    def test_rename_sdfield_tags_empty(self):
        html_input = '<p>Blah</p>'
        result = rename_sdfield_tags(html_input)
        expected = '<p>Blah</p>'
        assert result == expected

    def test_rename_sdfield_tags_nested(self):
        html_input = '<p>Blah<sdfield>12<span>b</span></sdfield></p>'
        result = rename_sdfield_tags(html_input)
        expected = '<p>Blah<span class="sdfield">12<span>b</span></span></p>'
        assert result == expected

    def test_cleanup_css_whitespace(self):
        css_input = 'p {font-family: ; font-size: 12px }'
        result, errors = cleanup_css(css_input)
        assert result == 'p{font-size:12px}'

    def test_cleanup_css_empty_style(self):
        css_input = 'p {}'
        result, errors = cleanup_css(css_input)
        assert result == ''

    def test_cleanup_css_empty_prop(self):
        css_input = 'p {font-family: ;}'
        result, errors = cleanup_css(css_input)
        assert result == ''

    def test_cleanup_css_empty_prop_no_colon(self):
        css_input = 'p {font-family: }'
        result, errors = cleanup_css(css_input)
        assert result == ''

    def test_cleanup_css_empty_prop_middle(self):
        css_input = 'p { foo: baz ; font-family: ; bar: baz}'
        result, errors = cleanup_css(css_input)
        assert result == 'p{foo:baz;bar:baz}'

    def test_cleanup_css_complex(self):
        css_sample = os.path.join(
            os.path.dirname(__file__), 'input', 'sample1.css')
        css_input = open(css_sample, 'rb').read()
        result, errors = cleanup_css(css_input)
        assert 'font-family: ;' not in result

    def test_cleanup_css_errors(self):
        css_input = 'p { foo: baz ; font-family: ; bar: baz}'
        result, errors = cleanup_css(css_input)
        assert 'ERROR PropertyValue: Unknown syntax' in errors
        assert 'WARNING Property: Unknown Property name' in errors

    def test_cleanup_css_non_minified(self):
        css_input = 'p { foo: baz ; bar: baz}'
        result, errors = cleanup_css(css_input, minified=False)
        assert result == 'p {\n    foo: baz;\n    bar: baz\n    }'

    def test_rename_html_img_links(self):
        # Make sure img links are modified
        html_input_path = os.path.join(
            os.path.dirname(__file__), 'input', 'image_sample.html')
        html_input = open(html_input_path, 'rb').read()
        html_output, img_map = rename_html_img_links(html_input, 'sample.html')
        assert 'image_sample_html_10a8ad02.jpg' not in html_output
        assert 'sample_4.jpg' in html_output
        assert len(img_map.keys()) == 4 # 4 images are in doc
        assert 'image_sample_html_10a8ad02.jpg' in img_map.keys()
        assert 'sample_4.jpg' in img_map.values()

    def test_rename_html_img_links_no_ext(self):
        html_input = '<img src="filename_without_ext" />'
        html_output, img_map = rename_html_img_links(html_input, 'sample.html')
        assert html_output == '<img src="sample_1" />'
        assert img_map == {u'filename_without_ext': u'sample_1'}

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
        html_input = u'<img src="file with ümlaut.gif" />'
        html_output, img_map = rename_html_img_links(html_input, 'sample.html')
        assert img_map == {u'file with \xfcmlaut.gif': u'sample_1.gif'}

    def test_rename_html_img_links_multiple_img(self):
        # Check that multiple links to same file get same target
        html_input = '<img src="a.gif" /><img src="a.gif" /><img src="b.gif" />'
        html_output, img_map = rename_html_img_links(html_input, 'sample.html')
        assert img_map == {u'a.gif': u'sample_1.gif', u'b.gif': u'sample_2.gif'}
        assert html_output == '%s%s' % (
            '<img src="sample_1.gif" /><img src="sample_1.gif" />',
            '<img src="sample_2.gif" />')

    def test_base64url_encode(self):
        assert base64url_encode(chr(251)+chr(239)) == '--8='
        assert base64url_encode(chr(255)*2) == '__8='

    def test_base64url_decode(self):
        assert base64url_decode('--8=') == chr(251) + chr(239)
        assert base64url_decode('__8=') == chr(255) * 2

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
