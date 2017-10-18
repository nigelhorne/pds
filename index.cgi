#!/usr/bin/perl
#
#########################################################################
#
# Image Display System    6/12/2001     
# John Moose    moosejc@muohio.edu
#
#########################################################################
#
# Please see the file "README" for more information.
#
#########################################################################
# 
# Copyright (c) 1999-2001, John Moose
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
# 
# -  Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# -  Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
# -  Neither the name of "Image Display System" nor the names of its
#    contributors may be used to endorse or promote products derived from
#    this software without specific prior written permission.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A
# PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE REGENTS OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
# PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
# LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
# NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
# 
#########################################################################


# Some changes by Nigel Horne <njh@bandsman.co.uk>

# Load modules
use strict;
use warnings;
require CGI;
use File::Basename;
use Time::Local;
use File::Find;
use File::Path;
use Image::Magick;
use Image::Info qw(image_info);
use lib qw(./);
use idsShared;
use CGI::Buffer { optimise_content => 1 };

readPreferences('./ids.conf');

$scaledOverlay->Read("site-images/previewicon.png"); # read in the "scaled" icon to overlay on scaled images

my ($lastVisit,       $imagetodisplay, %Exclude, $origMaxSize);
my ($newSearchString, @searchResultFiles, $albumsInAlbum);
  
my $preview = Image::Magick->new;
$query = new CGI;

readStats();

# Global variables:
my ($base,$path,$type) = fileparse($0, '\.[^.]+\z');
$idscgi = $base . $type; # get name of this script
my $mainpage=$path;
  
# Initialize time variables
my($time) = time();
$currentDate = &prettyTime($time, 'date');
$currentTime = &prettyTime($time, 'time');

########################################################################
# program main
processData();

readLocalization("localizations/".$localization.".txt");
$languageMenu = '<form method="post" action="'.$idscgi.'">
		 <select name="localization" size="1" onchange="this.form.submit()">';
foreach my $availableLang (@availableLocalizations) {
	$languageMenu .= '<option value="'.$availableLang.'"'.($availableLang eq $localization ? ' selected="selected"' : '').'>'.($languageMappings{$availableLang} ? $languageMappings{$availableLang} : $availableLang)."</option>\n";
}
$languageMenu .= '</select>';
$languageMenu .= '<noscript>&nbsp;<input type="submit" value="&nbsp;&nbsp;Select&nbsp;&nbsp;"></noscript>';
$languageMenu .= '</form>';

$themeMenu = '<form method="post" action="'.$idscgi.'">
	      <select name="theme" size="1" onchange="this.form.submit()">';
foreach my $availableTheme (@availableThemes) {
	if ($availableTheme !~ /CVS/) {
		$themeMenu .= '<option value="'.$availableTheme.'"'.($availableTheme eq $theme ? ' selected="selected"' : '').'>'.$availableTheme."</option>\n";
	}
}
$themeMenu .= '</select>';
$themeMenu .= '<noscript>&nbsp;<input type="submit" value="&nbsp;&nbsp;Select&nbsp;&nbsp;"></noscript>';
$themeMenu .= '</form>';

&getExcludes();

if ($mode eq 'home') {
	generateHome();
} elsif ($mode eq 'album') {
	&generateAlbum($albumtodisplay);
	generateHome();
	addStats("$albumtodisplay","album");
	writeStats();
} elsif ($mode eq 'image') {
	generateImage();
} elsif ($mode eq 'search') {
	generateSearchResults();
} else {
	$mode = 'home';
	generateHome();
}

if (($mode eq 'image') && ($allowPrints eq 'y') && ($fileExtension =~ /jpg|jpeg/i)) {
	openTemplate('imageSF');
} else {
	openTemplate($mode);
}

processVarTags();
renderPage();

########################################################################
# subfunctions

sub processData {
	# Interprets any form variables passed to the script. Checks to make sure the input makes sense.
	#
	my($cookieSort, $cookieMaxDimension, $cookieLocalization, $cookieTheme) = readCookie();
	
	if ($query->param('mode')) {
		$mode = $query->param('mode');
		chomp $mode;
		unless ($mode =~ /album|image|search/) {$mode = 'home';}
	} else {
		$mode = 'home';
	}
	
	if ($mode eq 'album') {
	    getAlbumToDisplay();
  		$startItem =  $query->param('startitem');
  	}

  	if ($mode eq 'image') {
	    getAlbumToDisplay();
		$imagetodisplay = $query->param('image') || bail ("Sorry, no image name was provided: $!");
  		
		if (($imagetodisplay =~ /\.\./) || ($albumtodisplay =~ /\.\./)) {
			bail ("Directory/image paths must not include \"../\".");
		}
	
  		unless (-e "albums$albumtodisplay/$imagetodisplay") { # does this album exist?
			bail ("Sorry, the image \"albums$albumtodisplay/$imagetodisplay\" doesn't exist: $!");
		}
	}
	
	if ($mode eq 'search') {
		$searchString = $query->param('searchstring') || bail ("Sorry, no search string was provided: $!");
  		unless ($searchString =~ /.{3,}/) {
			bail ("Sorry, search string must be 3 or more characters in length: $!");
  		}
  	}
	
	if ($cookieMaxDimension || $query->param('maxDimension')) {
		unless ($query->param('maxDimension')) {
			$maxDimension = $cookieMaxDimension if ($cookieMaxDimension =~ /\d+/);
		} else {
			$maxDimension = $query->param('maxDimension') if ($query->param('maxDimension') =~ /\d+/);
		}
	}
	
	if ($cookieSort || $query->param('sort')) {
		unless ($query->param('sort')) {
			$sort = $cookieSort;
		} else {
			$sort = $query->param('sort');
		}
		unless ($sort =~ /name|date|size|intelligent/) {
			$sort = 'name';
		}
	}
	
	if ($cookieLocalization || $query->param('localization')) {
		unless ($query->param('localization')) {
			$localization = $cookieLocalization;
		} else {
			$localization = $query->param('localization');
		}
		checkLocalization();
	}
	
	if ($allowUserTheme eq 'y') {
		if ($cookieTheme || $query->param('theme')) {
			unless ($query->param('theme')) {
				$theme = $cookieTheme;
			} else {
				$theme = $query->param('theme');
			}
			checkTheme()
		}
	}
	
}

sub generateAlbumEntry($@) {
  	my $album = shift(@_);
	my $Path='';
	$Path = shift if scalar @_;
 
 	my $origAlbum = $album;
   	$album =~ s/\balbums\///; # trims off 'albums/' from the filepath provided by glob.
  	$album =~ s/\/\Z//;# trims off the trailing slash from the filepath provided by glob.
	$album =~ s/\.\.\///;
	my $prettyalbum = $album;
	$prettyalbum =~ s/^\.+\///g; #trim off leading dot stuff
  	$prettyalbum =~ s/\#\d+_//g; # trims off numbers used for list ordering. ex: "#02_"
  	$prettyalbum =~ s/_/ /g; # replaces underscores with spaces
  	my $previewName = "$albumData/$album/".$theme.'.'.$albumIconName;
	unless (-e $previewName) {
		#warn "$album: creating preview $previewName $origAlbum";
  		$previewName = generateAlbumPreview($origAlbum);
  	}
	if (!defined $previewName || $previewName eq '') {
		$previewName = "site-images/$albumIconName";
  	}
	$previewName =~ s/\/{2,}/\//g;
  	my($xSize, $ySize) = &getImageDimensions("$previewName");
	'<span class="home-albumname"><a href="'.$idscgi.
	'?mode=album&amp;album='.&encodeSpecialChars($album).'">'."<img src=\"".&encodeSpecialChars($previewName)."\" border=\"0\" width=\"$xSize\" height=\"$ySize\" alt=\"[$prettyalbum]\" /><br />".$prettyalbum.'</a></span>'."\n";
}


sub generateHome {
	#produces the top-level page, incorporating a list of albums and site news (if available)
	#
	my @albums = Albums('./');	
	my($totalalbums) = ($#albums) + 1;
	
	$home = '<table border="0"><tr>';
	my($album);
	my($albumcounter) = 0;
	$homesingle = $home;
	
	foreach $album (sort @albums) {
  		$albumcounter ++;
		$home = $home . '<td align="center" valign="top" width="133">' . generateAlbumEntry($album) . '<br /><br /></td>';
  		$homesingle = $homesingle . '<td align="center" valign="top" width="133">' . generateAlbumEntry($album) . '<br /><br /></td></tr><tr>';
  		if ($albumcounter ge $imagesPerRow) { #create a multi-column list
  			unless ($albumcounter == ($#albums + 1)) {
  				$home = $home."</tr><tr>\n";
  			}
			$albumcounter = 0;
		}
	}
	
	if (($albumcounter ne 0)) {
		for (my $i = 0; $i < ($imagesPerRow - $albumcounter); $i++) {
			$home = $home."<td>&nbsp;</td>\n"; #put in cells to finish the row
			$homesingle = $homesingle."<td>&nbsp;</td>\n";
		}
	}
	
	$home = $home."</tr></table>\n";
	$homesingle =~ s/<tr>\Z//;
	$homesingle = $homesingle."</table>\n";
	
	if ($mode eq 'home') {
		$description = openItemDesc("$albumData/");	# read in site description
	}
	openNewsDesc("");	# read in site news
	
	$footer = $localization{'site-footer'};
	$footer =~ s/\%time/$currentTime/;
	$footer =~ s/\%date/$currentDate/;
	my $IDSVersion = "<a href=\"http://ids.sourceforge.net/\">IDS $VERSION</a>";
	$footer =~ s/\%version/$IDSVersion/;
}

sub getExcludes($) {
    # read in the 'exclude' list
    my @exclude=();
    my $excludeFile = "./$albumData/$albumtodisplay/exclude.txt";
    if (open (EXCL, "$excludeFile")) {
		chomp(@exclude=<EXCL>);
		close EXCL;
    }
    
    foreach my $I (@exclude) {
    	$Exclude{"albums/$albumtodisplay/$I"}++;
    }
}

sub getAlbumImages($) {
    my $albumtodisplay = shift;
	opendir ALBUMDIR, "albums/$albumtodisplay" || die ("can't open \"albums/$albumtodisplay\" album directory: ($!)");
	my @filesInAlbum = grep !/^\.+/, readdir ALBUMDIR;
	closedir ALBUMDIR;
	return @filesInAlbum;
}

sub probeAlbum ($) {
    my $albumtodisplay=shift;
    my @itemsToDisplay;
    my $albumsInAlbum=0;
    my $imagesInAlbum=0;
    foreach my $fileInAlbum (getAlbumImages($albumtodisplay)) {
		next if ($fileInAlbum =~ /CVS/); # this is a CVS directory- ignore it
		next if ($fileInAlbum =~ /_pre.jpg\Z/i); # this is an old-style preview image- ignore it
		next if ($fileInAlbum =~ /_disp\d*\.jpg\Z/i); # this is a display image- ignore it
    	$fileInAlbum = "albums/$albumtodisplay/" . $fileInAlbum;
	        next if exists $Exclude{$fileInAlbum};
			
		if (-d $fileInAlbum) { # Is this a subdirectory?
	        	push @itemsToDisplay, $fileInAlbum; # if so, remember its name
	        	$albumsInAlbum ++;
        }
        if (displayableItem($fileInAlbum)) { # is this a displayed format?
			push @itemsToDisplay, $fileInAlbum; # if so, remember its name
			$imagesInAlbum ++;
		}
	}
	
	($albumsInAlbum, $imagesInAlbum, @itemsToDisplay);
}
  

# produces an album, displaying thumbnail pictures with names and filesizes. 
# Displays a description of the album (if present).
sub generateAlbum($) {
	my $albumtodisplay=shift;
	my $linksToPages='';
	
	my ($previousalbumtemp);
	
	#Trim off useless /. path components
	$albumtodisplay =~ s/\/\.(?=\/)//g;
	
	# Build the previous albums link chain.
	
	# New code to generate previousalbum for albums. Code
	# integrated/swiped from up-n-coming IDS 1.0.

	my @pathElements = split('/', "$albumtodisplay");
	my $link = '';
	my @prevAlbums;
	push @prevAlbums, '<a href="'.$idscgi.'">'.$localization{'album-mainPageLink'}.'</a>';
	for (my $i = 1; $i <= $#pathElements; $i++) {
	    my $prettyAlbum = $pathElements[$i];
	    $prettyAlbum =~ s/\A\#\d+_//; # trims off numbers used for list ordering. ex: "#02_" (\A is like ^)
	    $prettyAlbum =~ s/_/ /g; # replaces underscores with spaces
	    $link .= ($link eq '' ? '' : '/') . &encodeSpecialChars($pathElements[$i]);
	    # Bold the current album name.
	    if ($i < $#pathElements) {
		push @prevAlbums, '<a href="'.$idscgi.'?mode=album&amp;album='.$link.'">'.$prettyAlbum.'</a>';
	    } else {
		push @prevAlbums, '<b>'.$prettyAlbum.'</b>';
		# Hey - this is the album name, too.
		$albumtitle = $prettyAlbum;
	    }    
	}

	$previousalbum = join(' &gt; ', @prevAlbums);
	
	my($imagecounter) = 0;
	if (!defined $startItem || $startItem eq '') {
  		$startItem = '1';
  	}
  	
	my($albumsInAlbum,$imagesInAlbum,@itemsToDisplay) = probeAlbum($albumtodisplay);
  
  	$albumitems = '<table border="0" cellpadding="5" cellspacing="0" width="100%">';
  	$albumitems = $albumitems."<tr>\n";
  	
  	my($rowsInAlbum) = 0;
	$imagecounter = 0;
  	my($startcounter) = 0;
  	my ($commentedItems) = 'n';
  	
  	foreach my $fileName (@itemsToDisplay) {
    	fillDateHash($fileName);
	}
	@itemsToDisplay = sortItems(@itemsToDisplay);
	
	# generate album HTML
	foreach my $itemToDisplay (@itemsToDisplay) {
  		$startcounter ++;
  		next if (($startcounter < $startItem) || ($startcounter > ($startItem + int($rowsPerPage * $imagesPerRow))));
		
		my($imageName) = $itemToDisplay;
		$imageName =~ s/([^\/]+)\/?$//; #trim off the directory path returned by glob
		$imageName = $1;
		
		my($base,$path,$type) = fileparse($itemToDisplay, '\.[^.]+\z');
		
		my($filesize) = &fileSize($itemToDisplay);
		
		
		my($previewImageSize);
  		if ($type =~ /jpg|jpeg|gif|png|tif/i) {	#this is a supported image file
			createDisplayImage($previewMaxDimension,'./',$itemToDisplay);
  			my($previewName) = &filenameToDisplayName($itemToDisplay, $previewMaxDimension);
			$previewName =~ s/\/{2,}/\//g;
  			my($xSize, $ySize) = &getImageDimensions("$previewName");
  			my($prettyImageTitle) = $base;
			$prettyImageTitle =~ s/\#\d+_//g;
			$prettyImageTitle =~ s/_/ /g;
			my ($commentMark) = '';
			my ($descPath) = $path;
			$descPath =~ s/albums\//$albumData/;
			if (-e ($descPath.$base.'_desc.txt') && (-s ($descPath.$base.'_desc.txt') > 0)) {
				$commentMark = '<span class="highlight">*</span>';
				$commentedItems = 'y';
			}
			my($filesize) = &fileSize($itemToDisplay);
			$albumitems = $albumitems."<td align=\"center\" valign=\"middle\"><div class=\"album-item\"><a href=\"".$idscgi."?mode=image&amp;album=".&encodeSpecialChars($albumtodisplay)."&amp;image=".&encodeSpecialChars($imageName)."\"><img src=\"".&encodeSpecialChars($previewName)."\" border=\"0\" width=\"$xSize\" height=\"$ySize\" alt=\"[$prettyImageTitle]\" /><br />$prettyImageTitle</a>$commentMark".($sort eq 'date' ? "<br />".prettyTime($mtime{$itemToDisplay},'date') : '') . ($sort eq 'size' ? "<br />$filesize" : ''). "</div></td>\n";
  		} elsif (-d $itemToDisplay) { # this is a directory
		
  			# create a link to the directory
			my $dirToDisplay = $itemToDisplay;
  			$imageName =~ s/\#\d+_//g; # trims off numbers used for list ordering. ex: "#02_"
  			$imageName =~ s/_/ /g;
			$dirToDisplay =~ s/\Aalbums\///;
			my $previewName = "$albumData$dirToDisplay/$theme.$albumIconName";
			unless (-e $previewName) {
				$previewName = generateAlbumPreview($itemToDisplay);
			}
			if ($previewName eq '') {
				$previewName = 'site-images/album_icon.png';
			}
  			my($xSize, $ySize) = &getImageDimensions("$previewName");
			my ($commentMark) = '';
			if (-e ("$albumData/$dirToDisplay/album_description.txt") && (-s ("$albumData/$dirToDisplay/album_description.txt") > 0)) {
				$commentMark = '<span class="highlight">*</span>';
				$commentedItems = 'y';
			}
			$albumitems = $albumitems."<td align=\"center\" valign=\"middle\"><div class=\"album-item\"><a href=\"".$idscgi."?mode=album&amp;album=".&encodeSpecialChars($dirToDisplay)."\"><img src=\"".&encodeSpecialChars($previewName)."\" border=\"0\" width=\"$xSize\" height=\"$ySize\" alt=\"[$imageName]\" /><br />$imageName</a>$commentMark". ($sort eq 'date' ? "<br />".prettyTime($mtime{$itemToDisplay},'date') : '') . ($sort eq 'size' ? "<br /><i>album</i>" : ''). "</div></td>\n";
		} else { #this is a generic file
			my $previewName;
			my $extension = $type;
			$extension =~ s/\.//;
			if (-e "site-images/filetypes/\L$extension".".png") {
				$previewName = "site-images/filetypes/\L$extension".".png";
			} elsif (-e "site-images/filetypes/\U$extension".".png") {
				$previewName = "site-images/filetypes/\U$extension".".png";
			} else {
				$previewName = "site-images/generic_file.png";
			}
  			my($xSize, $ySize) = &getImageDimensions("$previewName");
  			my($prettyImageTitle) = $base;
  			$prettyImageTitle =~ s/\#\d+_//g;
  			$prettyImageTitle =~ s/_/ /g;
			my($filesize) = &fileSize($itemToDisplay);
  			# create a link directly to the movie file
  			$albumitems = $albumitems."<td align=\"center\" valign=\"middle\"><div class=\"album-item\"><a href=\"albums/".&encodeSpecialChars("$albumtodisplay/$imageName")."\"><img src=\"".&encodeSpecialChars($previewName)."\" border=\"0\" width=\"$xSize\" height=\"$ySize\" alt=\"[$prettyImageTitle]\" /><br />$prettyImageTitle</a>".($sort eq 'date' ? "<br />".prettyTime($mtime{$itemToDisplay},'date') : '') . ($sort eq 'size' ? "<br />$filesize" : ''). "</div></td>\n";
		}
		
		$imagecounter ++;
		if ($imagecounter == $imagesPerRow) { #is it time to go to the next row?
			$albumitems = $albumitems."</tr>\n<tr>";
			$imagecounter = 0;
			$rowsInAlbum ++;
		}
		
		last if ($rowsInAlbum eq $rowsPerPage);
	}
	
	$albumitems =~ s/<tr>\Z//;
	
	if (($imagecounter ne $imagesPerRow) && ($imagecounter ne '0')) {
		for (my $i = 0; $i < ($imagesPerRow - $imagecounter); $i++) {
			$albumitems = $albumitems."<td>&nbsp;</td>\n"; #put in cells to finish the row (necessary for Netscape)
		}
		$albumitems = $albumitems."</tr>\n";
	}
	

	for (my $i = 0; $i < (($imagesInAlbum + $albumsInAlbum)/(int($rowsPerPage * $imagesPerRow))); $i++) {
		$linksToPages = $linksToPages .($i ne 0 ? " | " : "<br />");
		if (($i * (int($rowsPerPage * $imagesPerRow)) + 1) eq $startItem) {
			unless (($rowsPerPage * $imagesPerRow) >= ($imagesInAlbum + $albumsInAlbum)) {
				my $page = $localization{'album-pageNumber'};
				my $pageNumber = ($i + 1);
				$page =~ s/\%pageNumber/$pageNumber/;
				$linksToPages = $linksToPages . $page;
			}
		} else {
			my $page = $localization{'album-pageNumber'};
			my $pageNumber = ($i + 1);
			$page =~ s/\%pageNumber/$pageNumber/;
			$linksToPages = $linksToPages . "<a href=\"$idscgi?mode=album&amp;startitem=".(($i * int($rowsPerPage * $imagesPerRow)) + 1)."&amp;album=".&encodeSpecialChars($albumtodisplay)."\">$page</a>";
		}
	}
	
	my ($lastItem) = $startItem + (int($rowsPerPage * $imagesPerRow)) - 1;
	if ($lastItem > ($imagesInAlbum + $albumsInAlbum)) {
		$lastItem = ($imagesInAlbum + $albumsInAlbum);
	}
	
	$albumitems = $albumitems . "<tr>
									<td colspan=\"$imagesPerRow\" align=\"right\">
										<table width=\"100%\">
											<tr>
												<td valign=\"top\" align=\"left\">
													<span class=\"album-item\"><br />";
	
	if ((($imagesInAlbum + $albumsInAlbum) != 0)) {
		my $albumSummary = $localization{'album-itemCount'};
		$albumSummary =~ s/\%firstItem/$startItem/;
		$albumSummary =~ s/\%lastItem/$lastItem/;
		my $totalItems = ($imagesInAlbum + $albumsInAlbum);
		$albumSummary =~ s/\%totalItems/$totalItems/;
		
		if ((($imagesInAlbum + $albumsInAlbum) != 1)) {
			$albumitems = $albumitems . $albumSummary;
		} else {
			$albumitems = $albumitems . $localization{'album-oneItem'};
		} 
		
		$albumitems = $albumitems . "</span>
												</td>
												<td valign=\"top\" align=\"right\">
													<span class=\"album-pagelinks\">$linksToPages</span>
												</td>
											</tr>".($commentedItems eq 'y' ? '
											<tr>
												<td valign=\"top\">
													<span class="album-hascomments"><span class="highlight">*</span>'.$localization{'album-hasComments'}.'</span>
												</td>
											</tr>' : '')."
										</table>
									</td>
								</tr>";
	} else {
		$albumitems = $albumitems . $localization{'album-noItems'} ."</span>
												</td>
												<td valign=\"top\" align=\"right\">
													<span class=\"album-pagelinks\">$linksToPages</span>
												</td>
											</tr>
										</table>
									</td>
								</tr>";
	}
	
	
	$albumitems = $albumitems.'</table>';
	
	$description = openItemDesc("$albumData$albumtodisplay/");	# read in album desc

	$lastModified = &prettyTime((stat("albums/$albumtodisplay"))[9]);
	
	$sortMethod = "
		<form action=\"$idscgi\" method=\"get\">
		<input type=\"hidden\" value=\"album\" name=\"mode\" />
		<input type=\"hidden\" value=\"$albumtodisplay\" name=\"album\" />
		<select name=\"sort\" size=\"1\" onchange=\"this.form.submit()\">
			<option value=\"".'name'."\"".($sort eq 'name' ? ' selected="selected"' : '').">".$localization{'album-sortName'}."</option>
			<option value=\"".'date'."\"".($sort eq 'date' ? ' selected="selected"' : '').">".$localization{'album-sortDate'}."</option>
			<option value=\"".'size'."\"".($sort eq 'size' ? ' selected="selected"' : '').">".$localization{'album-sortSize'}."</option>
			<option value=\"".'intelligent'."\"".($sort eq 'intelligent' ? ' selected="selected"' : '').">".$localization{'album-sortIntelligent'}."</option>
		</select>	
		<noscript>
		&nbsp;<br /><br /><input type=\"submit\" value=\"&nbsp;&nbsp;".$localization{'album-sortButton'}."&nbsp;&nbsp;\">
		</noscript>
		</form>";
	
	$footer = $localization{'site-footer'};
	$footer =~ s/\%time/$currentTime/;
	$footer =~ s/\%date/$currentDate/;
	my $IDSVersion = "<a href=\"http://ids.sourceforge.net/\">IDS $VERSION</a>";
	$footer =~ s/\%version/$IDSVersion/;
}

sub generateImage {
	#produces the a page to display an image. Provides image size, dimensions, type, and date uploaded. Can display a description (if present).
	#
	$albumtitle = $albumtodisplay;
	my($origXSize, $origYSize) = my($displayXSize, $displayYSize) = &getImageDimensions("albums/$albumtodisplay/$imagetodisplay");
	
	if ($origXSize >= $origYSize) {
		$origMaxSize = $origXSize;
	} else {
		$origMaxSize = $origYSize;
	}
	
	my($startItem) = 1;
  	
	my($albumsInAlbum, $imagesInAlbum, @itemsToDisplay) = probeAlbum($albumtodisplay);
  	
  	my ($imageCounter) = 0;
  	
	@itemsToDisplay = sortItems(@itemsToDisplay);
	
	foreach my $itemToDisplay (@itemsToDisplay) {
		$imageCounter ++;
		my($imageName) = $itemToDisplay;
		$imageName =~ s/([^\/]+)\/?$//; #trim off the directory path returned by glob
		$imageName = $1;
		last if ($imageName eq $imagetodisplay);
	}
	
	for (my $i = 0; $i < (($imagesInAlbum + $albumsInAlbum)/($rowsPerPage * $imagesPerRow)); $i++) {
		if (($imageCounter > ($i * ($rowsPerPage * $imagesPerRow))) && ($imageCounter <= (($i * ($rowsPerPage * $imagesPerRow)) + ($rowsPerPage * $imagesPerRow)))) {
			$startItem = 1 + ($i * ($rowsPerPage * $imagesPerRow));
		}
	}
	
	# New code to generate previousalbum for images. Code
	# integrated/swiped from up-n-coming IDS 1.0.

	my @pathElements = split('/', "$albumtodisplay");
	my $link = '';
	my @prevAlbums;
	push @prevAlbums, '<a href="'.$idscgi.'">'.$localization{'album-mainPageLink'}.'</a>';
	for (my $i = 1; $i <= $#pathElements; $i++) {
	    my $prettyAlbum = $pathElements[$i];
	    $prettyAlbum =~ s/\A\#\d+_//; # trims off numbers used for list ordering. ex: "#02_" (\A is like ^)
	    $prettyAlbum =~ s/_/ /g; # replaces underscores with spaces
	    $link .= ($link eq '' ? '' : '/') . &encodeSpecialChars($pathElements[$i]);
	    # Bold the current album name.
	    push @prevAlbums, ($i == $#pathElements ? '<b>' : '')
		.'<a href="'.$idscgi.'?mode=album&amp;album='.$link.'">'.$prettyAlbum.'</a>'
		    .($i == $#pathElements ? '</b>' : '');
	}
	
	$previousalbum = join(' &gt; ', @prevAlbums);


	my @imagesForPrevNextTmp = grep !/\.mov\Z|\.mpg\Z|\.mpeg\Z|\.mp3\Z/i, @itemsToDisplay; # for prev/next thumbs
	my @imagesForPrevNext;
	
	foreach my $prevnextTmp (@imagesForPrevNextTmp) {
		if (!(-d $prevnextTmp) && ($prevnextTmp =~ /jpg\Z|jpeg\Z|gif\Z|png\Z|tif\Z/i)) {
			$prevnextTmp =~ s/.+\///;
			push @imagesForPrevNext, $prevnextTmp;
		}
	}
  
	my $where=0;
  	for ($[ .. $#imagesForPrevNext) {
		$where = $_, last if ($imagesForPrevNext[$_] eq "$imagetodisplay");
  	}
  	
  	$prevthumb = '';
  	$prevtextthumb = '';
  	$nextthumb = '';
  	$nexttextthumb = '';
  	
	if ($where > 0)	{ $prevthumb = generatePrevNext($albumtodisplay,$imagesForPrevNext[$where-1],"&lt; ".$localization{'image-previousImage'},'image'); }
	if ($where > 0)	{ $prevtextthumb = generatePrevNext($albumtodisplay,$imagesForPrevNext[$where-1],"&lt; ".$localization{'image-previousImage'},'text'); }
	createDisplayImage($previewMaxDimension, './', $imagesForPrevNext[$where-1]);
	createDisplayImage($previewMaxDimension, './', $imagesForPrevNext[$where+1]) if $where+1 < scalar @imagesForPrevNext;
	if ($where < $#imagesForPrevNext) { $nextthumb = generatePrevNext($albumtodisplay,$imagesForPrevNext[$where+1], $localization{'image-nextImage'}." &gt;",'image'); }
  	if ($where < $#imagesForPrevNext) { $nexttextthumb = &generatePrevNext($albumtodisplay,$imagesForPrevNext[$where+1], $localization{'image-nextImage'}." &gt;",'text'); }

	if (( -r "albums/$albumtodisplay/.ids_size")  && ($maxDimension eq '')) {
		open (ALBUMSIZE, "<albums/$albumtodisplay/.ids_size") || warn "can't open albums/$albumtodisplay/.ids_size";
		$maxDimension = <ALBUMSIZE>;
		close (ALBUMSIZE);
		$maxDimension =~ s/\n//; # remove trailing newline
		unless ($maxDimension =~ /^\d+\Z/) {
			$maxDimension = '';
			warn "ignoring bad size constraint $maxDimension";
		}
	}

	my($filesize) = my($newFilesize) = &fileSize("albums/$albumtodisplay/$imagetodisplay");
	
	if (($maxDimension =~ /^\d+\Z/) && ($maxDimension < $origMaxSize)) {
		createDisplayImage($maxDimension,'./',"albums/$albumtodisplay/$imagetodisplay");
		my $imagetoreallydisplay = &filenameToDisplayName("albums/$albumtodisplay/$imagetodisplay", $maxDimension);
		($displayXSize, $displayYSize) = &getImageDimensions("$imagetoreallydisplay");
		$image = "<img src=\"".&encodeSpecialChars("$imagetoreallydisplay")."\" width=\"$displayXSize\" height=\"$displayYSize\" alt=\"[$imagetodisplay]\" />";
		$newFilesize = &fileSize("$imagetoreallydisplay");
	} else {
		my $Src = "albums/$albumtodisplay/$imagetodisplay";
		$Src =~ s/\/{2,}/\//g;
		$image = "<img src=\"".&encodeSpecialChars($Src)."\" width=\"$displayXSize\" height=\"$displayYSize\" alt=\"[$imagetodisplay]\" />";
  	}
	
	my($imageNameTrimmed) = $imagetodisplay;
	$imageNameTrimmed =~ s/\.([^.]+)\Z//;
	$fileExtension = $1;
	
	my $embeddedComments;
	
	if ($displayImageData eq 'y') {
		my($picinfo) = image_info("albums/$albumtodisplay/$imagetodisplay");
		if (defined($picinfo->{'Comment'})) {
			$embeddedComments = join("<br />\n", $picinfo->{'Comment'});
	  	} else {
	  		#Set the embeddedComments string to null, so we don't have to keep checking
			$embeddedComments='<i>'.$localization{'image-noComments'}.'</i>';
	  	}
		if (defined $embeddedFilter) {
 		    $embeddedComments =~ s/$embeddedFilter//i; # remove arbitrary signatures
  		}
  	} else {
  		$embeddedComments='';
  	}
  	
  	$description = openItemDesc("$albumData/$albumtodisplay/$imageNameTrimmed");
	
	if ($description eq '') {
		$description = '<i>'.$localization{'image-noComments'}.'</i>';
	}
	
	if (defined $guestComments && $guestComments eq 'y') {
		$description = $description . "<br /><div align=\"right\">
				<form action=\"postcomment/postcomment.cgi\" method=\"get\">
					<input type=\"hidden\" value=\"createcomment\" name=\"mode\" />
					<input type=\"hidden\" value=\"$albumtodisplay\" name=\"album\" />
					<input type=\"hidden\" value=\"$imagetodisplay\" name=\"image\" />
					<input type=\"submit\" value=\"&nbsp;&nbsp;".$localization{'image-commentButton'}."&nbsp;&nbsp;\" />
				</form></div>";
	}

	my($daysSinceMod) = (-M "albums/$albumtodisplay/$imagetodisplay");
	
	if (int($daysSinceMod + .5) < 2) {
		$daysSinceMod = $localization{'image-infoUploaded2'};
	} else {
		my $modTemp = $localization{'image-infoUploaded1'};
		$daysSinceMod = int($daysSinceMod);
		$modTemp =~ s/\%days/$daysSinceMod/;
		$daysSinceMod = $modTemp;
	}
	
	if ($fileExtension =~ /jpg|jpeg/i) {
		$fileExtension = "JPEG";
	} elsif ($fileExtension =~ /gif/i) {
		$fileExtension = "GIF";
	} elsif ($fileExtension =~ /png/i) {
		$fileExtension = "PNG";
	} 
	
	
	my $cam_iso;
	if ($displayImageData eq 'y') {
		 no strict 'refs'; #Otherwise, we'll get the dreaded "Can't use string ("x") as an ARRAY ref while 'strict refs'"
		my($camerainfo) = image_info("albums/$albumtodisplay/$imagetodisplay");
		if (defined($camerainfo->{'ISOSpeedRatings'})) {
			$cam_iso = $camerainfo->{'ISOSpeedRatings'};
		} else {
			$cam_iso = "<i>".$localization{'image-infoUnknown'}."</i>";
		}
		
		my $top;
		if (defined($camerainfo->{'ExposureTime'})) {
		    my @I_exp = $camerainfo->{'ExposureTime'};
		    $top = $I_exp[0][1] / $I_exp[0][0], unless ($I_exp[0][1] == 0);
		} elsif (defined($camerainfo->{'ShutterSpeedValue'})) {
		    my @frac = $camerainfo->{'ShutterSpeedValue'};
		    my $time;

		    if ($frac[0][1] == 0) {
		        $time = $frac[0][0];
		    } else {
		        $time = $frac[0][0] / $frac[0][1];
		    }
		    $top = int (0.5 + exp($time * log(2)));
		}

		my $cam_exp;
		unless ($top <= 1) {
			$cam_exp = '1/' . int($top) . 's';
		} else {
			$cam_exp = "<i>".$localization{'image-infoUnknown'}."</i>";
		}
		
		my @f_n;
	  	if (defined($camerainfo->{'FNumber'})) {
	  		@f_n = $camerainfo->{'FNumber'};
		} elsif (defined($camerainfo->{'ApertureValue'})) {
			@f_n = $camerainfo->{'ApertureValue'};
		}

	    my ($cam_f, $cam_flen);
		if (!scalar @f_n || $f_n[0][1] == 0) {
		  $cam_f = "f" . $f_n[0] if scalar @f_n && defined $f_n[0];
	  	} else {
	  		$cam_f = "f" . $f_n[0][0] / $f_n[0][1], 
	  	}
	  	
	  	if ($cam_f eq "") {
	  		$cam_f = "<i>".$localization{'image-infoUnknown'}."</i>";
	  	}
	  	
		my @fl_n = $camerainfo->{'FocalLength'};
	  	if (defined($camerainfo->{'FocalLength'})) {
	  		if ($fl_n[0][1] == 0) {
					$cam_flen = int($fl_n[0]*5) . "mm";
			} else {
					$cam_flen = int(5*$fl_n[0][0]/$fl_n[0][1]) . "mm", unless ($fl_n[0][1] == 0);
			}
		} else {
			$cam_flen = "<i>".$localization{'image-infoUnknown'}."</i>";
		}
		
		my($cam_flash, $cam_date, $cam_model);
		my $cam_make = '';
		
		if (defined($camerainfo->{'Flash'})) {
			$cam_flash = $camerainfo->{'Flash'};
		} else {
			$cam_flash = "<i>".$localization{'image-infoUnknown'}."</i>";
		}
		if ((defined($camerainfo->{'DateTimeOriginal'})) && ($camerainfo->{'DateTimeOriginal'} ne '0000:00:00 00:00:00')) {
			$cam_date = $camerainfo->{'DateTimeOriginal'};
		} else {
			$cam_date = "<i>".$localization{'image-infoUnknown'}."</i>";
		}
		if (defined($camerainfo->{'Make'})) {
			$cam_make = $camerainfo->{'Make'};
			$cam_make =~ s/;*\Z//; # Some cameras end this field with a semi-colon
		}
		if (defined($camerainfo->{'Model'})) {
			$cam_model = $camerainfo->{'Model'};
			$cam_model =~ s/;*\Z//; # Some cameras end this field with a semi-colon
		} else {
			$cam_model = "<i>".$localization{'image-infoUnknown'}."</i>";
		}
		
		if (length $cam_make) {
			$caminfo = $localization{'image-infoCameraMake'}.": "."$cam_make"."<br />".$localization{'image-infoCameraModel'}.": $cam_model<br />".$localization{'image-infoFlash'}.": $cam_flash<br />".$localization{'image-infoDate'}.": $cam_date<br />";
			$caminfo2 = $localization{'image-infoISO'}.": $cam_iso<br />".$localization{'image-infoFocalLength'}.": $cam_flen<br />".$localization{'image-infoShutter'}.": $cam_exp<br />".$localization{'image-infoAperture'}.": $cam_f<br />";
		} else {
			$caminfo = (defined $embeddedComments && $embeddedComments ne '' ? $localization{'image-infoEmbedded'}.':<br />'.$embeddedComments : '');
		}
		
		$pictureinfo = $localization{'image-infoType'}.": $fileExtension<br />".$localization{'image-infoFileSize'}.": $newFilesize ($filesize)<br />".$localization{'image-infoImageSize'}.": $displayXSize"."x"."$displayYSize ($origXSize"."x"."$origYSize)<br />".$localization{'image-infoUploaded'}.": $daysSinceMod";
	}
	
	$imagetitle = $imageNameTrimmed;
	$imagetitle =~ s/\#\d+_//g;
	$imagetitle =~ s/_/ /g;
	
	$imageResizer = "
		<form action=\"$idscgi\" method=\"get\">
		<input type=\"hidden\" value=\"image\" name=\"mode\" />
		<input type=\"hidden\" value=\"$albumtodisplay\" name=\"album\" />
		<input type=\"hidden\" value=\"$imagetodisplay\" name=\"image\" />
		<select name=\"maxDimension\" size=\"1\" onchange=\"this.form.submit()\">
			".(512 < $origMaxSize ? "<option value=\"512\"".($maxDimension eq '512' ? ' selected="selected"' : '').">".$localization{'image-imageSizeTiny'}." (512)</option>" : '')."
			".(640 < $origMaxSize ? "<option value=\"640\"".($maxDimension eq '640' ? ' selected="selected"' : '').">".$localization{'image-imageSizeSmall'}." (640)</option>" : '')."
			".(800 < $origMaxSize ? "<option value=\"800\"".($maxDimension eq '800' ? ' selected="selected"' : '').">".$localization{'image-imageSizeMedium'}." (800)</option>" : '')."
			".(1024 < $origMaxSize ? "<option value=\"1024\"".($maxDimension eq '1024' ? ' selected="selected"' : '').">".$localization{'image-imageSizeLarge'}." (1024)</option>" : '')."
			".(1600 < $origMaxSize ? "<option value=\"1600\"".($maxDimension eq '1600' ? ' selected="selected"' : '').">".$localization{'image-imageSizeXLarge'}." (1600)</option>" : '')."
			<option value=\"9999\"";
	if ($maxDimension >= $origMaxSize) {
		$imageResizer = $imageResizer . ' selected="selected"';
	}
	$imageResizer = $imageResizer . ">".$localization{'image-imageSizeOriginal'}."</option>
		</select>
		<noscript>
		&nbsp;<input type=\"submit\" value=\"&nbsp;&nbsp;".$localization{'image-imageSizeButton'}."&nbsp;&nbsp;\">
		</noscript>
		</form>";
	
	my ($bigImageURL) = $query->url;
	$bigImageURL =~ s/\/[^\/]+\Z/\//;
	my ($thumbURL) = $bigImageURL;
	$bigImageURL .= &encodeSpecialChars("albums$albumtodisplay/$imagetodisplay");
	
	unless (($maxDimension > $origMaxSize) || ($maxDimension eq '9999')) {
		$thumbURL .= &encodeSpecialChars("image-cache$albumtodisplay/".$imageNameTrimmed."_disp".$maxDimension.".jpg");
	} else {
		$thumbURL = $bigImageURL;
	}
	
	my ($selfURL) = $query->self_url;
	$selfURL =~ s/\&/\&amp;/g;
	if (($allowPrints eq 'y') && ($fileExtension =~ /jpg|jpeg/i)) {
		$orderPrintsForm = '
			<form action="http://www.shutterfly.com/c4p/UpdateCart.jsp" method="post">
				<input type="hidden" name="addim" value="1" />
				<input type="hidden" name="protocol" value="SFP,100" />
				<input type="hidden" name="pid" value="C4P" />
				<input type="hidden" name="psid" value="AFFL" />
				<input type="hidden" name="referid" value="IDS'.$VERSION.'" />
				<input type="hidden" name="returl" value="'.$selfURL.'" />
				<input type="hidden" name="imraw-1" value="'.$bigImageURL.'" />
				<input type="hidden" name="imrawheight-1" value="'.$origYSize.'" />
				<input type="hidden" name="imrawwidth-1" value="'.$origXSize.'" />
				<input type="hidden" name="imthumb-1" value="'.$thumbURL.'" />
				<input type="hidden" name="imbkprnta-1" value="'.$siteTitle.'" />
				<input type="submit" value="&nbsp;&nbsp;'.$localization{'image-orderPhotoButton'}.'&nbsp;&nbsp;" />
			</form>';
	}
	
	$footer = $localization{'site-footer'};
	$footer =~ s/\%time/$currentTime/;
	$footer =~ s/\%date/$currentDate/;
	my $IDSVersion = "<a href=\"http://ids.sourceforge.net/\">IDS $VERSION</a>";
	$footer =~ s/\%version/$IDSVersion/;
	addStats("$albumtodisplay/$imagetodisplay","$fileExtension");
	writeStats();
}

sub generateSearchResults {
	$newSearchString = $searchString;
	$newSearchString =~ s/\./\\./g;  # turn '.' into '\.' (dot is regex wildcard)
	$newSearchString =~ s/\?/\\S/g;  # turn '?' into '\S' (perl's way of doing a one char match)
	$newSearchString =~ s/\*/\\S+/g;  # turn '*' into '\S+' (perl's way of doing a many char match)
	
	my (@filenames) = split (/\s+/, $newSearchString);
	
	find ({wanted => \&searchForFiles, follow_fast=>1}, "./albums/");
	
	my $fileNameTemp;
	foreach $fileNameTemp (@filesToSearch) {
		unless ($fileNameTemp =~ /\/.+\.\S\S\S\S?\Z/) { 
			$fileNameTemp = $fileNameTemp . '/'; 
		}
		
		my($descfilepath) = $fileNameTemp;
		my ($textToSearch) = $fileNameTemp;

		$textToSearch =~ /\/([^\/]+\/?)$/; #trim off directory path
		$textToSearch = $1;
		
		next if ($fileNameTemp =~ /^albums\/\Z/); #this is just the albums directory.
		
		my($base,$path,$type) = fileparse($fileNameTemp, '\.[^.]+\z');
		
		$descfilepath =~ s/$type\Z//;
		$descfilepath =~ s/\A\.\/albums/$albumData/;
		
		my($descriptionTmp) = openItemDesc("$descfilepath");
		
		next unless (($textToSearch =~ /$newSearchString/ig) || ($descriptionTmp =~ /$newSearchString/ig));
		
		$descriptionTmp =~ s/::://;
		$fileNameTemp =~ s/\A\.\///;
		
		push (@searchResultFiles, ($textToSearch. ':::' .$fileNameTemp . ':::' . $descriptionTmp));
	}
	
	
	
	$searchResults = '<table border="0" cellpadding="5" cellspacing="0" width="100%">';
	
	# generate album HTML
	my ($imagesInAlbum) = 0;
	my ($albumsInAlbum) = 0;
	my ($itemToDisplay);
	my ($trash);
  	foreach $itemToDisplay (sort @searchResultFiles) {
		my ($trash, $itemToDisplay, $descriptionTmp) = split (/:::/, $itemToDisplay);
  		my($pathtofile) = $itemToDisplay;
  		$itemToDisplay =~ s/\A.+\/\/\///;
		createDisplayImage($previewMaxDimension,'./',$itemToDisplay); #create preview
  		$imagesInAlbum ++;
  		$searchResults .= "<tr>\n";
  		unless ($imagesInAlbum eq 1) {
			$searchResults .= "<td colspan=\"2\"><hr noshade=\"noshade\" size=\"1\" width=\"200\" />\n</td></tr><tr>";
		}
		
		my($base,$path,$type) = fileparse($itemToDisplay, '\.[^.]+\z');
		
		my($imageName) = $itemToDisplay;
		$imageName =~ s/([^\/]+)\/?$//; #trim off the directory path returned by glob
		$imageName = $1;
		
		$albumtodisplay = $itemToDisplay;
		$albumtodisplay =~ /^(.+)\/([^\/]+)$/;
		$albumtodisplay = $1;
  		$albumtodisplay =~ s/albums\///;
		my $dirToDisplay = $albumtodisplay;
  		
  		my($previewImageSize);
  		my($prettyImageTitle);
  		if ($type =~ /jpg|jpeg|gif|png|tif/i) {	#this is a supported image file
			my($previewName) = &filenameToDisplayName($itemToDisplay, $previewMaxDimension);
			my($xSize, $ySize) = &getImageDimensions("$previewName");
			my($imageNameTrimmed) = $imageName;
			$imageNameTrimmed =~ s/\.([^.]+)\Z//;
			$prettyImageTitle = $imageName;
			$prettyImageTitle =~ s/\#\d+_//g;
			$prettyImageTitle =~ s/($newSearchString)/<span class="highlight"><b>$1<\/b><\/span>/isg;
			$searchResults = $searchResults."<td align=\"center\" valign=\"top\"><a href=\"".$idscgi."?mode=image&amp;album=".&encodeSpecialChars($albumtodisplay)."&amp;image=".&encodeSpecialChars($imageName)."\"><img src=\"".&encodeSpecialChars($previewName)."\" border=\"0\" width=\"$xSize\" height=\"$ySize\" alt=\"[$imageName]\" /></a></td>\n";
		} elsif (-d $itemToDisplay) { # this is a directory
			# create a link to the directory
			$dirToDisplay = $itemToDisplay;
			$imageName =~ s/\#\d+_//g; # trims off numbers used for list ordering. ex: "#02_"
			$imageName =~ s/_/ /g;
			$prettyImageTitle = $imageName;
			$prettyImageTitle =~ s/\#\d+_//g;
			$prettyImageTitle =~ s/($newSearchString)/<span class="highlight"><b>$1<\/b><\/span>/isg;
			$dirToDisplay =~ s/\Aalbums\///;
			$dirToDisplay =~ s/\/\Z//;
			my $previewName = "$albumData/$dirToDisplay/".$theme.'.'.$albumIconName;
			unless (-e $previewName) {
				$previewName = generateAlbumPreview($itemToDisplay);
			}
			if (!defined $previewName || $previewName eq '') {
				$previewName = 'site-images/album.jpg';
			}
			my($xSize, $ySize) = &getImageDimensions("$previewName");
			$searchResults = $searchResults."<td align=\"center\" valign=\"middle\"><a href=\"".$idscgi."?mode=album&amp;album=".&encodeSpecialChars($dirToDisplay)."\"><img src=\"".&encodeSpecialChars($previewName)."\" border=\"0\" width=\"$xSize\" height=\"$ySize\" alt=\"[$imageName]\" /></a></td>\n";
			$dirToDisplay =~ s/[\/]*$albumtodisplay//;
		} else {  #this is a generic file
			my $previewName;
			my $extension = $type;
			$extension =~ s/\.//;
			if (-e "site-images/filetypes/\L$extension".".png") {
				$previewName = "site-images/filetypes/\L$extension".".png";
			} elsif (-e "site-images/filetypes/\U$extension".".png") {
				$previewName = "site-images/filetypes/\U$extension".".png";
			} else {
				$previewName = "site-images/generic_file.png";
			}
  			my($xSize, $ySize) = &getImageDimensions("$previewName");
  			$prettyImageTitle = $imageName;
			$prettyImageTitle =~ s/\#\d+_//g;
			$prettyImageTitle =~ s/($newSearchString)/<span class="highlight">$1<\/span>/isg;
			# create a link directly to the movie file
			$searchResults = $searchResults."<td align=\"center\" valign=\"middle\"><a href=\"albums/".&encodeSpecialChars("$albumtodisplay/$imageName")."\"><img src=\"".&encodeSpecialChars($previewName)."\" border=\"0\" width=\"$xSize\" height=\"$ySize\" alt=\"[$imageName]\" /></a></td>\n";
		}
		
		$descriptionTmp = '>'.$descriptionTmp;
		$descriptionTmp =~ s/(>[^<]*)($newSearchString)/$1<span class="highlight"><b>$2<\/b><\/span>/isg;
		$descriptionTmp =~ s/\A>//;
		
		if ($descriptionTmp eq '') {
			$descriptionTmp = "<i>".$localization{'image-noComments'}."</i>";
		}
		
		$searchResults = $searchResults."<td valign=\"top\" width=\"300\"><div class=\"search-results\"><b>$prettyImageTitle</b><p />".$localization{'search-comments'}.": $descriptionTmp <p />".$localization{'search-location'}.": <a href=\"".$idscgi. ($dirToDisplay ne '' ? "?mode=album&amp;album=".&encodeSpecialChars($dirToDisplay) : "")."\">/".$dirToDisplay."</a><br />".$localization{'search-lastMod'}.": ".&prettyTime((stat("$pathtofile"))[9])."</div><br /></td>";
		
		$searchResults = $searchResults."</tr>\n";
	}
	
	if (($imagesInAlbum eq '') and ($albumsInAlbum eq '')) {$searchResults = $searchResults. "<td colspan=\"2\"><span class=\"search-results\">".$localization{'search-noHits'}."</span></td>";}
	
	$searchResults = $searchResults.'</table>';
	
	$totalitems = $imagesInAlbum + $albumsInAlbum;
	if ($totalitems == 1) {
		$totalitems = $localization{'search-counter1'};
	} else {
		my $temp = $localization{'search-counter'};
		$temp =~ s/\%foundItems/$totalitems/;
		$totalitems = $temp;
	}
	
	$previousalbum = "<a href=\"$idscgi\">&lt; ".$localization{'search-mainPageLink'}."</a>";
	$footer = $localization{'site-footer'};
	$footer =~ s/\%time/$currentTime/;
	$footer =~ s/\%date/$currentDate/;
	my $IDSVersion = "<a href=\"http://ids.sourceforge.net/\">IDS $VERSION</a>";
	$footer =~ s/\%version/$IDSVersion/;
}

sub searchForFiles {
	push (@filesToSearch, $File::Find::name);
}

sub openNewsDesc {
	# open news file found at given path
	#
	# each line of an IDS newsfile takes the following format:
	#          news date:::news subject:::news body
	#
	my $path;
	$path = shift(@_) if scalar @_;
  	my $file;
  
	if ( defined $path && $path ne "" ) { $path = "$path/"; }
  
  	# try to open "local_news.html", "site_news.html", "site_news.txt"
	# first come, first serve

	$file = $path.'site_news.txt';
	
	$sitenews = '<table border="0">';
	
	if (open (NEWS, $file)) {
		line2: 
		while (<NEWS>) {
			next line2 if $_ =~ /^#|^\n/; #skip comments and blank lines
			chomp $_;
			my($newsDate, $newsSubject, $newsBody) = split(/:::/, $_);
			$newsBody =~ s/\|\|\|/\n/g;
			$newsDate =~ s/\A(\d\d\d\d)(\d\d)(\d\d)(\d\d)(\d\d)\d\d\Z/$2\/$3\/$1<br \/>$4:$5/;
			$sitenews .= "<tr><td valign=\"top\" align=\"center\"><span class=\"home-newsdate\">$newsDate</span></td><td valign=\"top\"><span class=\"home-newsbody\"><b>$newsSubject</b></span></td></tr><tr><td></td><td><div class=\"home-newsbody\">$newsBody<br /><br /></div></td></tr>";
		}
		close (NEWS) || die ("can't close \"$file\": ($!)");
	} else {
		$sitenews = "<tr><td>Sorry, no news file found at \"$file\".</td></tr>";
	}
	
	$sitenews .= '</table>';
}
