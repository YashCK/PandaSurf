
<h1 align="center">
  PandaSurf
  <br>
</h1>

<h4 align="center">A Browser Built From Scratch.</h4>

<p align="center">
  <a href="#key-features">Key Features</a> •
  <a href="#how-to-use">How To Use</a> •
  <a href="#download">Download</a> •
  <a href="#related">Related</a> •
  <a href="#license">License</a>
</p>

<!-- Online Diff Eq Notes -->

### Ex: This is how you can use the browser
[![PandaSurf Demo](Helper/VideoDisplay.png)](https://www.youtube.com/watch?v=7CqXEiQak7o)

## Key Features

Supports HTTP, HTTPS, File, Data, and View-Source schemes.

- When a URL is entered, it parses the HTML/CSS from the HTTP response, and displays the webpage.
- You can scroll up/down and zoom in/out(font increases/decreases in size)
- Clicking on a hyperlink, takes you to the URL clicked on
- You can open multiple tabs to search multiple websites, and also go back in history for any one
- Allows for searching for links by typing in the address bar
- Browser can be adjusted in size

* URL Parsing (HTTP / HTTPS) \[https://.....]
  - HTML Parser
    - Goes through the source code and constructs the DOM tree of tags and text
    - Is not confused my html attributes
    - Fixes any malformed html (deals with html, head, body as implicit tags)
    - Adjust text based on tag (\<b> to bold, \<i> to italicize, \<small>, \<big>, etc...)
    - Supports special characters &lt;, \&gt;, &amp;, $shy;, "&quot;
  - Layout Engine
    - A tree based structure used to model a page's layout tree
    - Each node in the tree corresponds to a layout object (Text/Heading/Section of Page) 
      - Blocks/Sections, Lines, Words, and the Entire Documents all correspond to a Layout object
    - Compute size and position of each object
    - Allows to render backgrounds
  - CSS Parser
    - Support style attributes and linked CSS files
    - Implemented cascading and inheritance
    - Support different font properties
      - color, font-weight, font-style, and font-size 
    - Support tag selectors, descendent selectors, class selectors
    - Added support for both style attributes and linked CSS files;
  - Supports Content-Encoding, Transfer-Encoding, Cache-Control Headers
  - Addresses URLs which are redirects
  - Caches URLs and fetches/deletes resources depending on if they are fresh 

* File \[file:///.....]
  - Primarily for Text Files
  - Displays File Content

* Data \[data:.....]
  - MIME Types: text/plain , text/html
  - Reads optional parameters and can decode custom encoding and base64
  - Displays page content

* View-Source \[view-source:.....]
  - Displays the source of the http/https URL requested with correct formatting
  - Uses Syntax Highlighting to show Text in a Bold Font

## How To Use

A release of this application is not available yet.

> **Note**
> If you're using a Mac, you may need to Install Certificates for SSL. You can [see this guide]([ssl-certification-for-mac/](https://stackoverflow.com/questions/52805115/certificate-verify-failed-unable-to-get-local-issuer-certificate)) to address the certification issue with SSL.
> Running Install Certificates.command should fix the issue.
> Additionally updating your version of python (install through brew) could work.


## Download

A release of this application is not available yet.

## Related

Nothing currently

## License

IDK
