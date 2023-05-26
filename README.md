
<h1 align="center">
  <!--
  <br>
  <a href="http://www.amitmerchant.com/electron-markdownify"><img src="https://raw.githubusercontent.com/amitmerchant1990/electron-markdownify/master/app/img/markdownify.png" alt="Markdownify" width="200"></a>
  <br>
   --> 
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

<img width="622" alt="Screen Shot 2023-05-25 at 11 29 55 PM" src="https://github.com/YashCK/PandaSurf/assets/43621900/7b1f0a59-d7fe-49e2-8f5d-cfcafed76c25">

<img width="1286" alt="Screen Shot 2023-05-25 at 11 26 34 PM" src="https://github.com/YashCK/PandaSurf/assets/43621900/0c071512-cc38-4bd2-91b8-8787824591fa">

## Key Features

Supports HTTP, HTTPS, File, Data, and View-Source schemes.

* URL Parsing (HTTP / HTTPS) \[https://.....]
  - HTML Parser
    - Goes through the source code and constructs the DOM tree of tags and text
    - Is not confused my html attributes
    - Fixes any malformed html (deals with html, head, body as implicit tags)
    - Adjust text based on tag (\<b> to bold, \<i> to italicize, \<small>, \<big>, etc...)
  - Layout Engine
    - A tree based structure used to model a page's layout tree
    - Each node in the tree corresponds to a layout object (Text/Heading/Section of Page) 
    - Compute size and position of each object
    - Allows to render backgrounds
  - CSS Parser
    - Support style attributes and linked CSS files
    - Implemented cascading and inheritance
    - Support different font properties
      - color, font-weight, font-style, and font-size 
    - Support tag selectors and descendent selectors
    - Added support for both style attributes and linked CSS files;
  - Displays text in the body of the HTTP Response (including special characters &lt;, \&gt;)
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

## Alternate Examples

<!-- View Source Missing Semester -->

### View-Source Scheme

<img width="623" alt="Screen Shot 2023-05-25 at 11 29 36 PM" src="https://github.com/YashCK/PandaSurf/assets/43621900/79fa85df-aba4-4c91-9872-058ac1ff34f8">

<img width="1167" alt="Screen Shot 2023-05-25 at 11 27 51 PM" src="https://github.com/YashCK/PandaSurf/assets/43621900/3b9d9f76-ba9f-45a7-9855-eab920b467bb">

<img width="1168" alt="Screen Shot 2023-05-25 at 11 28 12 PM" src="https://github.com/YashCK/PandaSurf/assets/43621900/3e380989-1fa6-40f3-bb2a-df753eedf940">

### Another HTTPS Scheme

<img width="1002" alt="Screen Shot 2023-05-25 at 11 43 53 PM" src="https://github.com/YashCK/PandaSurf/assets/43621900/17574042-5c74-42f6-8bb3-eaf798035b76">
