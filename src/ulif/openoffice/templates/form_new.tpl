<html>
  <head>
    <title>Create a new doc</title>
  </head>
  <body>
    <form method="POST" action="{target_url}" enctype="multipart/form-data">
      <fieldset>
        <legend>Submit a document</legend>
        <label for="doc">File to convert:</label>
        <input type="file" name="doc" />
        <br />
        <label for="out_fmt">Format to convert to:</label>
        <select name="out_fmt">
          <option value="html" selected="selected">HTML</option>
          <option value="pdf" selected="selected">PDF</option>
        </select>
        <br />
        <input type="submit" name="CREATE" value="Send" />
      </fieldset>
    </form>
  </body>
</html>
