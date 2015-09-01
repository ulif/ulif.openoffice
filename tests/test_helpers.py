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
import pytest
import shutil
import stat
import tempfile
import unittest
import zipfile
from io import StringIO, BytesIO
from six import string_types
from ulif.openoffice.processor import OOConvProcessor
from ulif.openoffice.helpers import (
    copytree, copy_to_secure_location, get_entry_points, unzip, zip,
    remove_file_dir, extract_css, cleanup_html, cleanup_css,
    rename_html_img_links, rename_sdfield_tags, base64url_encode,
    base64url_decode, string_to_bool, strict_string_to_bool,
    string_to_stringtuple, filelike_cmp, write_filelike)
from ulif.openoffice.helpers import basestring as basestring_modified


class TestCopyTree(object):
    # Tests for copytree helper function.

    def test_copytree_ignore(self, tmpdir):
        # we can pass a function to ignore files
        def ignore(src, names):
            return ['sample1.txt', ]
        src_dir = tmpdir.mkdir("work")
        dest_dir = tmpdir.mkdir("dest")
        src_dir.join("sample1.txt").write("Hi!")
        src_dir.join("sample2.txt").write("Ho!")
        copytree(str(src_dir), str(dest_dir), ignore=ignore)
        assert dest_dir.join("sample1.txt").exists() is False
        assert dest_dir.join("sample2.txt").exists() is True

    def test_copytree_subdirs(self, tmpdir):
        # subdirs are copied as well
        tmpdir.mkdir("src_dir").mkdir("sub1")
        copytree(
            str(tmpdir.join("src_dir")), str(tmpdir.join("dest_dir")))
        assert tmpdir.join("dest_dir").join("sub1").isdir() is True

    def test_copytree_links(self, tmpdir):
        # we copy links
        tmpdir.mkdir("src_dir").join("sample.txt").write("Hi")
        os.symlink(
            str(tmpdir / "src_dir" / "sample.txt"),
            str(tmpdir / "src_dir" / "sample.link"))
        copytree(
            str(tmpdir / "src_dir"), str(tmpdir / "dest_dir"), symlinks=True)
        dest_link = tmpdir / "dest_dir" / "sample.link"
        assert os.path.islink(str(dest_link))
        assert os.readlink(str(dest_link)) == str(
            tmpdir / "src_dir" / "sample.txt")

    def test_copytree_ioerror(self, tmpdir):
        # we catch IOErrors, collect them and raise at end (as shutil.Error)
        src_dir = tmpdir.mkdir("src_dir")
        dst_dir = tmpdir.mkdir("dst_dir")
        src_dir.join("sample1.txt").write("Hi!")
        dst_dir.join("sample1.txt").write("Ho!")

        # make dst_file unwriteable
        dst_file_path = str(dst_dir / "sample1.txt")
        old_mode = os.stat(dst_file_path).st_mode
        os.chmod(dst_file_path, stat.S_IREAD)
        with pytest.raises(shutil.Error) as exc_info:
            copytree(
                str(src_dir), str(dst_dir), symlinks=False)
        os.chmod(dst_file_path, old_mode)      # reenable writing
        assert exc_info.type == shutil.Error
        err_src, err_dst, err_msg = exc_info.value.args[0][0]
        assert err_src == str(src_dir / "sample1.txt")
        assert err_dst == dst_file_path
        assert "Permission denied:" in err_msg
        assert dst_file_path in err_msg

    def test_copytree_detects_nested_dirs(self, tmpdir):
        # we detect dst dirs being part/subdirs of src dir.
        tmpdir.mkdir("root_dir").mkdir("sub_dir")
        with pytest.raises(ValueError) as why:
            copytree(str(tmpdir / "root_dir"),
                     str(tmpdir / "root_dir" / "sub_dir"))


class TestRemoveFileDir(object):
    # tests for remove_file_dir()

    def test_remove_file_dir_none(self):
        # we do not complain about files that do not exist
        assert remove_file_dir(None) is None

    def test_remove_file_dir_non_path(self):
        # we do not complain about objects that are not file paths
        assert remove_file_dir(object()) is None

    def test_remove_file_dir_not_existing(self):
        # we do not complain about not existing file paths
        assert remove_file_dir('not-existing-path') is None

    def test_remove_file_dir_file(self, tmpdir):
        # When we remove a file, also the containung dir is removed
        tmpdir.join("sample_dir").mkdir()
        tmpdir.join("sample_dir").join("sample.txt").write("Hi!")
        remove_file_dir(str(tmpdir / "sample_dir" / "sample.txt"))
        assert tmpdir.exists() is True
        assert tmpdir.join("sample_dir").exists() is False

    def test_remove_file_dir_dir(self, tmpdir):
        # We remove a directory if given as argument, of course.
        tmpdir.join("sample_dir").mkdir()
        tmpdir.join("sample_dir").join("sample.txt").write("Hi!")
        remove_file_dir(str(tmpdir / "sample_dir"))  # different to above
        assert tmpdir.exists() is True
        assert tmpdir.join("sample_dir").exists() is False


class TestExtractCSS(object):
    # tests for extract_css() helper.

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

    def test_extract_css_contains_all_styles_from_input(self, samples_path):
        # Extracted CSS contains all styles from input HTML
        content = samples_path.join("sample2.html").read()
        html, css = extract_css(content, "sample.html")
        assert css == (
            "@page { size: 21cm 29.7cm; margin: 2cm }\n"
            "p { margin-bottom: 0.21cm }\n"
            "span.c2 { font-family: DejaVu Sans Mono, sans-serif }\n"
            "span.c3 { font-family: DejaVu Sans Mönö, sans-serif }\n"
            "p.c1 { margin-bottom: 0cm }\n  \n  "
        )

    def test_extract_css_puts_links_into_html(self, samples_path):
        # the returned HTML part has the styles replaced with a link:
        content = samples_path.join("sample2.html").read()
        html, css = extract_css(content, "sample.html")
        assert html == (
            '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"\n'
            '    "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">\n'
            '\n'
            '<html xmlns="http://www.w3.org/1999/xhtml">\n'
            '<head>\n'
            '<meta content="HTML Tidy for Linux/x86 (vers 6 November 2007)'
            ', see www.w3.org" name="generator"/>\n'
            '<meta content="text/html; charset=utf-8" '
            'http-equiv="CONTENT-TYPE"/>\n'
            '<title></title>\n'
            '<meta content="OpenOffice.org 2.4 (Linux)" name="GENERATOR"/>\n'
            '<meta content="Uli Fouquet" name="AUTHOR"/>\n'
            '<meta content="20110517;485000" name="CREATED"/>\n'
            '<meta content="Uli Fouquet" name="CHANGEDBY"/>\n'
            '<meta content="20110517;524000" name="CHANGED"/>\n'
            '<link href="sample.css" rel="stylesheet" type="text/css"/>\n'
            '\n'
            '</head>\n'
            '<body dir="ltr" lang="de-DE" xml:lang="de-DE">\n'
            '<p class="c1">Some text</p>\n'
            '<p class="c1"><br/></p>\n'
            '<p class="c1">with <b>bold</b> and <i>italic</i> fonts.</p>\n'
            '<p class="c1"><br/></p>\n'
            '<p class="c1">Also a <span class="c2">complete different\n'
            '  font</span> is here. With umlaut: ä</p>\n'
            '<p class="c1">Finally, some\n'
            '    <span class="c2">seam</span><span>less text.</span>\n'
            '</p>\n'
            '<p class="c1"><br/></p>\n'
            '</body>\n'
            '</html>\n'
            )

    def test_extract_css_utf8(self):
        # we do not stumble over umlauts.
        result, css = extract_css(
            "<html><body>äö</body></html>", 'sample.html')
        assert css is None
        assert result == '<html><body>äö</body></html>'

    def test_extract_css_utf8_unicode(self):
        # we can handle umlauts in unicode-strings.
        result, css = extract_css(
            u"<html><body>ä</body></html>", 'sample.html')
        assert css is None
        assert result == u'<html><body>ä</body></html>'
        return

    def test_extract_css_complex_html(self, samples_path):
        # Make sure we have styles purged and replaced by a link
        html_input = samples_path.join("sample2.html").read()
        result, css = extract_css(html_input, 'sample.html')
        assert '<style' not in result
        link = '<link href="sample.css" rel="stylesheet" type="text/css"/>'
        assert link in result
        return

    def test_extract_css_complex_css(self, samples_path):
        # Make sure we get proper external stylesheets.
        html_input = samples_path.join("sample2.html").read()
        result, css = extract_css(html_input, 'sample.html')
        assert len(css) == 210
        assert css.startswith('@page { size: 21cm')
        return

    def test_extract_css_no_empty_comments(self, samples_path):
        # Make sure there are no empty comments in CSS
        html_input = samples_path.join("sample2.html").read()
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


class TestCleanupHTML(object):
    # tests for cleanup_html().

    def test_cleanup_html_fix_img_links(self, samples_path):
        # we do fix links to images.
        html_input = samples_path.join("image_sample.html").read()
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
        result, img_map = cleanup_html(
            html_input, 'sample.html', fix_sdfields=False)
        assert html_input == result

    def test_cleanup_html_no_minify_by_default(self):
        # by default, cleanup_html does not minify code
        html_input = '<span>\n<span>foo</span>\n</span>'
        result, img_map = cleanup_html(html_input, 'sample.html')
        assert result == html_input


class TestRenameSDFieldTags(object):
    # tests for rename_sdfield_tags() helper

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


class TestCleanupCSS(object):
    # tests for cleanup_css() helper.

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
        css_input = open(css_sample, 'r').read()
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


class TestRenameHTMLImgLinks(object):
    # tests for renam_html_img_links() helper.

    def test_rename_html_img_links(self, samples_path):
        # Make sure img links are modified
        html_input = samples_path.join('image_sample.html').read()
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
        key = list(img_map.keys())[0]
        val = list(img_map.values())[0]
        assert isinstance(key, string_types)
        assert isinstance(val, string_types)

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


class TestHelpersNew(object):

    def test_basestring(self):
        # our own basestring version works around py3 probs.
        assert isinstance("foo", basestring_modified) is True
        assert isinstance(b"foo", basestring_modified) is True
        assert isinstance(u"foo", basestring_modified) is True

    def test_copy_to_secure_location_file(self, workdir):
        # we can copy files to a secure location.
        workdir.join("src").join("sample.txt").write("Hey there!")
        result_path = copy_to_secure_location(
            str(workdir / "src" / "sample.txt"))
        assert os.path.isfile(os.path.join(result_path, "sample.txt"))

    def test_copy_to_secure_location_path(self, workdir):
        # we can copy dirs to a secure location
        workdir.join("src").join("sample.txt").write("Hey there!")
        result_path = copy_to_secure_location(str(workdir / "src"))
        assert os.path.isfile(os.path.join(result_path, 'sample.txt'))

    def test_get_entry_points(self):
        # get_entry_points really delivers our processors (maybe more)
        result = get_entry_points('ulif.openoffice.processors')
        assert result['oocp'] is OOConvProcessor

    def test_unzip(self, tmpdir):
        # make sure we can unzip filetrees
        zip_file = str(tmpdir / "sample.zip")
        shutil.copy(
            os.path.join(os.path.dirname(__file__), 'input', 'sample1.zip'),
            zip_file)
        dst = tmpdir.mkdir("dst")
        unzip(zip_file, str(dst))
        assert dst.listdir() == [dst  / 'somedir']
        assert sorted(os.listdir(str(dst.join("somedir")))) == [
            'othersample.txt', 'sample.txt']

    def test_zip_file(self, workdir):
        # make sure we can zip single files
        workdir.join("sample_dir").mkdir()
        sample_file = workdir.join("sample_dir").join("sample.txt")
        sample_file.write("A sample")
        result_path = zip(str(sample_file))
        assert zipfile.is_zipfile(result_path)

    def test_zip_dir(self, workdir):
        # make sure we can zip complete dir trees
        dir_to_zip = workdir / "src"
        dir_to_zip.join("subdir1").mkdir()
        dir_to_zip.join("subdir2").mkdir().join("subdir21").mkdir()
        dir_to_zip.join("subdir2").join("sample.txt").write("A sample")
        result_path = zip(str(dir_to_zip))
        zip_file = zipfile.ZipFile(result_path, 'r')
        result = sorted(zip_file.namelist())
        assert sorted(result) == [
            'sample.txt', 'subdir1/',
            'subdir2/', 'subdir2/sample.txt', 'subdir2/subdir21/']
        assert zip_file.testzip() is None

    def test_zip_invalid_path(self):
        # we get a ValueError if zip path is not valid
        with pytest.raises(ValueError) as why:
            zip("not-a-valid-path")
        assert why.type == ValueError

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
        with pytest.raises(ValueError) as why:
            strict_string_to_bool('nonsense')


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
            StringIO('asd'), StringIO('qwe')) is False
        assert filelike_cmp(
            StringIO('asd'), StringIO('asd')) is True
        p1 = os.path.join(self.workdir, 'p1')
        p2 = os.path.join(self.workdir, 'p2')
        p3 = os.path.join(self.workdir, 'p3')
        with open(p1, 'w') as fd:
            fd.write('asd')
        with open(p2, 'w') as fd:
            fd.write('qwe')
        with open(p3, 'w') as fd:
            fd.write('asd')
        assert filelike_cmp(p1, p2) is False
        assert filelike_cmp(p1, p3) is True
        assert filelike_cmp(p1, StringIO('asd')) is True
        assert filelike_cmp(StringIO('qwe'), p2) is True

    def test_filelike_cmp_w_bytes(self):
        # we can compare bytestreams
        assert filelike_cmp(
            BytesIO(b'asd'), BytesIO(b'qwe')) is False
        assert filelike_cmp(
            BytesIO(b'asd'), BytesIO(b'asd')) is True
        p1 = os.path.join(self.workdir, 'p1')
        p2 = os.path.join(self.workdir, 'p2')
        p3 = os.path.join(self.workdir, 'p3')
        with open(p1, 'wb') as fd:
            fd.write(b'asd')
        with open(p2, 'w') as fd:
            fd.write('qwe')
        with open(p3, 'w') as fd:
            fd.write('asd')
        assert filelike_cmp(p1, p2) is False
        assert filelike_cmp(p1, p3) is True
        assert filelike_cmp(p1, BytesIO(b'asd')) is True
        assert filelike_cmp(BytesIO(b'qwe'), p2) is True

    def test_filelike_cmp_multiple_time(self):
        # make sure filepointers are reset when we use the same
        # file-like object several times (as often happens in loops).
        p1 = os.path.join(self.workdir, 'p1')
        with open(p1, 'w') as fd:
            fd.write('foo')
        filelike1 = StringIO('foo')
        filelike2 = StringIO('bar')
        assert filelike_cmp(p1, filelike1) is True
        assert filelike_cmp(p1, filelike2) is False
        assert filelike_cmp(p1, filelike1) is True
        assert filelike_cmp(p1, filelike2) is False

    def test_write_filelike(self):
        src = os.path.join(self.workdir, 'f1')
        with open(src, 'w') as fd:
            fd.write('content')
        dst = os.path.join(self.workdir, 'f2')
        write_filelike(open(src, 'r'), dst)
        assert open(dst, 'r').read() == 'content'
        write_filelike(b'different', dst)
        assert open(dst, 'r').read() == 'different'
