pds
===

# Photography Display System

Create a [VWF](//github.com/nigelhorne/vwf) website to display your images.

Photographs are organized into sections, which in turn are organized into albums.
For example, you could have an album called "holiday pictures" which contains
sections such as "trip to India 2017" in which you put your photographs.

# Database Format

Each of the above databases (albums, sections, photographs) are stored in simple CSV
files (XML and SQLite are also supported) in the databases directory.
The only "gotcha" is that fields are separated by '!' not ','.
The first line of each file lists the fields in the file.

## albums.csv

Entry | Title
--- | ---
Album: "A", followed by a number | Free text
A1 | Pictures of England

## sections.csv

Entry | Section | Title
--- | --- | ---
Album: "A", followed by a number | Section: "S" followed by a number | Free text
A1 | S1 | Pictures of Margate

## photographs.csv

Entry | Section | Photograph | File | Title
--- | --- | --- | --- | ---
Album: "A", followed by a number | Section: "S" followed by a number | Photograph: "P" followed by a number | Filename in /img | Free text
A1 | S1 | P1 | Margate.jpeg | Margate Clock Tower - taken from the Wikipedia page

## /img

The images are put in album/section, in the above example that means .../img/A1/S1/Margate.jpeg

# Installation

Create a $hostname.com file in the conf directory
(use default as a template),
then modify the contents of the template tree so that the site looks as you
want it.
The configuration file can be in any number of formats including INI and XML.

    rootdir: /full/path/to/website directory
    SiteTitle: The title of your website
    memory_cache: where short-term volatile information is stored, such as the country of origin of the client
    disc_cache: where long-term information is stored, such as copies of output to see if HTTP 304 can be returned
    contact: your name and e-mail address

# Adding a photograph

To upload, store picture in img/A?/S? (e.g. img/A4/S2/tulip.jpg)
Run "bin/mkthumbs img/A4/S2 thumbs/A4/S2"
Edit the following files in the databases directory:
* albumbs.csv
* sections.csv
* photographs.csv

# Acknowledgements

So many Perl CPAN modules that if I list them all I'll miss one.

Magnific Popup http://dimsemenov.com/plugins/magnific-popup/

# TODO

* Thumbnails and Image::Info

* Finish print.css

# LICENSE AND COPYRIGHT

Copyright 2017-2023 Nigel Horne.

This program is released under the following licence: GPL2 for personal use on
a single computer.
All other users (for example Commercial, Charity, Educational, Government)
must apply in writing for a licence for use from Nigel Horne at `<njh at nigelhorne.com>`.
