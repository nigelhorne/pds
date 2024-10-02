#########################################################################
#
# Image Display System Shared Module	   7/27/2001
# John Moose	moosejc@muohio.edu
# Ashley M. Kirchner	amk4@users.sourceforge.net
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
#	notice, this list of conditions and the following disclaimer.
# -  Redistributions in binary form must reproduce the above copyright
#	notice, this list of conditions and the following disclaimer in the
#	documentation and/or other materials provided with the distribution.
# -  Neither the name of "Image Display System" nor the names of its
#	contributors may be used to endorse or promote products derived from
#	this software without specific prior written permission.
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



BEGIN {
	use Exporter();
	use vars qw(@EXPORT @EXPORT_OK %EXPORT_TAGS @ISA);
	@ISA = qw(Exporter);
	%EXPORT_TAGS= ();
	@EXPORT_OK =qw($mode $startItem $imagetodisplay $currentTime $currentDate
		%Exclude $origMaxSize $newSearchString
		$searchBox $searchString $searchResults
		$siteTitle $siteHeader $siteFooter $sitenews $pathToJpegTran
		$description $idscgi  $VERSION
		$footer  $adminContent $guestComments $commentAbuserFilter $lastModified $home $homesingle
		$albumtodisplay @FilesToPreview @AlbumsToPreview
		$albumtitle $albumitems $albumIconName $localization %localization
		$maxDimension $imageQuality $imageCache $albumData $theme @availableThemes
		$previewMaxDimension $scaledImageBorderWidth $fileTypes @fileTypes @availableLocalizations
		$displayScaledIcon $scaledOverlay $allowPrints $languageMenu $themeMenu
		$prevthumb $prevtextthumb $previousalbum $embeddedFilter %languageMappings
		$nextthumb $nexttextthumb @filesToSearch
		$image $imagetitle $imageResizer $pictureinfo $caminfo $caminfo2
		$totalitems $pageContent $imagesPerRow $rowsPerPage
		$Layers1 $Layers2 $displayImageData $orderPrintsForm
		$query $fileExtension %mtime $sortMethod $sort $logDir
		$commentContent $sortMethod $maxDisplayedComments $allowUserTheme @stats $collectstats);
}

use vars @EXPORT_OK;

$VERSION="0.82";

# Create Defaults (The values in ids.conf override these.)
$maxDimension = 640;
$previewMaxDimension = 100;
$imagesPerRow = 3;
$rowsPerPage = 4;
$scaledImageBorderWidth = 1;
$displayScaledIcon = 'n';
$imageQuality = 85;
$guestComments = 'n';
$commentAbuserFilter = 'n';
$siteTitle = 'image display system';
$siteHeader = 'your site\'s name here';
$siteFooter = 'all images &copy; 2003';
$displayImageData = 'y';
$allowPrints = 'n';
$maxDisplayedComments = 10;
$sortMethod = $sort = 'name';
$home ='';
$homesingle ='';
$sitenews='';
$idscgi='index.cgi';
$searchString='';
$adminContent='';
$albumIconName='album_icon.png';
$pathToJpegTran='';
$localization='English';
$theme='Sharp Grey';
$embeddedFilter = '';
$allowUserTheme = 'y';
$fileTypes = 'jpg jpeg gif png tif mov mpg mpeg mp3';
$collectstats = 'n';
$commentContent = '';
$albumtodisplay = '';
$imageCache="image-cache";
$albumData="album-data";
$logDir="logs";
$scaledOverlay = Image::Magick->new;

use POSIX;
use Fcntl;
use strict qw(vars);
use CGI::Carp qw (fatalsToBrowser);

1;

sub fillDateHash {
	my $fileName = shift;
	my($camdate,$camtime);
	my($picinfo) = image_info($fileName);
	if ((defined($picinfo->{'DateTimeOriginal'})) && ($picinfo->{'DateTimeOriginal'} ne '0000:00:00 00:00:00')&& ($picinfo->{'DateTimeOriginal'} =~/\A\d\d\d\d\:\d\d\:\d\d \d\d\:\d\d\:\d\d\Z/ )) {
		$camdate = $picinfo->{'DateTimeOriginal'};
		my ($date,$time) = split / /, $camdate;
		my ($year,$month,$day) = split /:/, $date;
		my ($hour,$min,$sec) = split /:/, $time;
		$month--;
		$year -= 1900;
		$camtime = timelocal($sec,$min,$hour,$day,$month,$year);
		$mtime{$fileName} = $camtime;
	} else {
		my $modTime = (stat $fileName)[9];
		$mtime{$fileName} = $modTime;
	}
}

# sort passed items using the sort method specified in $sort
sub sortItems {
	my @itemsToSort = @_;
	if ($sort eq 'intelligent') {
		@itemsToSort = sort intelligent_sort @itemsToSort;
	} elsif ($sort eq 'date') {
		foreach my $fileName (@itemsToSort) {
			fillDateHash($fileName);
		}
		@itemsToSort = sort date_sort @itemsToSort;
	} elsif ($sort eq 'size') {
		@itemsToSort = sort size_sort @itemsToSort;
	} else {
		@itemsToSort = sort @itemsToSort;
	}
	return @itemsToSort;
}

sub date_sort {
	$mtime{$b} <=> $mtime{$a}; # most recent items first
}

sub size_sort {
	(-s $b) <=> (-s $a); # biggest files first
}

# My own comparison routine to sort words & number pairs more the way that
# humans find natural. RCM
sub intelligent_sort {
	my $la1= lc($a);
	my $lb1= lc($b);
	my ($la2, $la3, $lb2, $lb3);
  
	# First see if the strings have numerical components
	if ($la1 =~ /^(.*)(\d+)(.*)$/) {$la1=$1; $la2=$2; $la3=$3;}
	if ($lb1 =~ /^(.*)(\d+)(.*)$/) {$lb1=$1; $lb2=$2; $lb3=$3;}
  
	# If both have leading strings, compare these; we don't return if they are
	# equal.

	if (defined $la1) {
		my $c1=0;
		if (defined $lb1) {
			$c1 = ($la1 cmp $lb1);
		} else {
		return -1;
		}
		return $c1 if $c1;
	} elsif (defined $lb1) {
		return 1;
	}

	# next compare the numbers part
	my $c2=0;
	$c2 = ($la2 <=> $lb2) if defined $la2 && defined $lb2;
	return $c2 if $c2;
  
	# compare trailing string
	my $c3=0;
	$c3 = ($la3 cmp $lb3) if defined $la3 && defined $lb3;
	return $c3;
}

# Replace a file, but only after the replacement has been created.
# The new file is created to a temporary name (and deleted if the program exits
# or is killed before the replacement is done).	The second parameter should be
# a coderef that will will called and passed the filehandle.	When the coderef
# completes the original file will be replaced with the new file.	On error,
# the new file is deleted without replacing the old file.	RCM
sub replace_file($&) {
	my $File=shift;
	die "No file to save to!" unless $File;
	$File =~ s/\A\///;
	my $Sub =shift;
	local *FH;
	my $name;
	# try new temporary filenames until we get one that didn't already
	# exist;	the check should be unnecessary, but you can't be too careful
	for (my $i = 0; $i <= 100; $i++) { #give up after 99 tries
		$name = "$File.$$-".int rand 999;
		last if (sysopen(FH, $name, O_RDWR|O_CREAT|O_EXCL));
		die "Couldn't create temporary file: ($!)" if $i == 100;
	}

	# install atexit-style handler so that when we exit or die,
	# we automatically delete this temporary file
	END {
		if (defined $name) {
			unlink($name) or die "Couldn't unlink $name .$!";
		}
	}

	# now go on to use the file ...
	$Sub->(\*FH);

	close FH;
	my $R = rename $name, $File;
	# "Couldn't rename $name .$!";
	unlink $name unless $R;
	$name=undef;
	return $R;
}

sub Albums($) {
	my $ppath = shift;
	$ppath = '' unless defined $ppath;
	#returns the names of all directories in the 'albums' directory
	my $DIR;
	opendir DIR, $ppath."albums";
	my @albums;
	foreach (sort readdir DIR) {
		if ((!/CVS/) && /^([^\.].*)$/ && -d $ppath."albums/$1") {
			push @albums, $ppath."albums/$1";
		}
	}
	closedir DIR;
	@albums;
}

sub readCookie {
	if ($query->cookie(-name=>'IDS_site_prefs')) {
		my($cookieSort, $cookieMaxDimension, $cookieLocalization, $cookieTheme) = split(/\|\|/, $query->cookie(-name=>'IDS_site_prefs'));
		return ($cookieSort, $cookieMaxDimension, $cookieLocalization, $cookieTheme);
	}
	return 0;
}

sub getAlbumToDisplay(@) {
	my $ppath = shift;
	$ppath = './' if !defined $ppath;
	$albumtodisplay = $query->param('album') || bail ("Sorry, no album name was provided: $!");

	if ($albumtodisplay =~ /\.\./) { # hax0r protection...
		bail ("Sorry, invalid directory name: $!");
	}
	if ($albumtodisplay ne '/' && !-e $ppath . "albums/$albumtodisplay") { # does this album exist?
		bail ("Sorry, the album \"$albumtodisplay\" doesn't exist: $!");
	}

	$albumtodisplay = '/' . $albumtodisplay;
	$albumtodisplay =~ s/\/\//\//g;
}

# adds text to the end of a log file
sub appendLogFile {
	my($fileToOpen) = shift(@_);
	my($textToAppend) = shift(@_);
	my($oldContents);

	if (-e $fileToOpen) {
		open (LOG, $fileToOpen) || bail ("can't open $fileToOpen: ($!)");
		$oldContents = (join '', <LOG>);
		close (LOG) || bail ("can't close $fileToOpen: ($!)");
	}
	my($user);
	if (defined $query) {
		$user = $query->remote_host();
	} else {
		$user = 'localhost';
	}	
	($currentDate, $currentTime) = initTime();
	$main::newLogContents = $oldContents . "\n_______________________\n$currentDate $currentTime - ".$user."\n" . $textToAppend;

	replace_file($fileToOpen,
		sub
		{
		local *FH = shift;
		print FH $main::newLogContents;
		});
}

# Converts "odd" characters into web-safe sequences. For example, " " 
# (space) becomes "%20".
sub encodeSpecialChars($) {
	my($textToEncode) = shift(@_);
	$textToEncode =~ s/([^a-zA-Z0-9_\-\.\/])/sprintf("%%%02x",ord($1))/ge;
	return $textToEncode;
}

# Reads in an ids preferences file (ids.conf)
sub readPreferences {
	my ($prefsFile) = shift(@_);
	my (%preference);
	open (PREFS,$prefsFile) || warn ("can't open preferences \"$prefsFile\": ($!)");
	while (<PREFS>) {
		next if $_ =~ /^#|^\n/; #skip comments and blank lines
		chomp $_;
		my($tagtitle, $tagvalue) = split(/\t/, $_);
		$preference{$tagtitle} = $tagvalue;
	}
	close (PREFS) || bail ("can't close preferences: ($!)");
	$maxDimension = $preference{maxDimension} if exists $preference{maxDimension};
	$previewMaxDimension = $preference{previewMaxDimension} if exists $preference{previewMaxDimension};
	$imagesPerRow = $preference{imagesPerRow} if exists $preference{imagesPerRow};
	$rowsPerPage = $preference{rowsPerPage} if exists $preference{rowsPerPage};
	$scaledImageBorderWidth = $preference{scaledImageBorderWidth} if exists $preference{scaledImageBorderWidth};
	$displayScaledIcon = $preference{displayScaledIcon} if exists $preference{displayScaledIcon};
	$imageQuality = $preference{imageQuality} if exists $preference{imageQuality};
	$guestComments = $preference{guestComments} if exists $preference{guestComments};
	$siteTitle = $preference{siteTitle} if exists $preference{siteTitle};
	$siteHeader = $preference{siteHeader} if exists $preference{siteHeader};
	$siteFooter = $preference{siteFooter} if exists $preference{siteFooter};
	$displayImageData = $preference{displayImageData} if exists $preference{displayImageData};
	$allowPrints = $preference{allowPrints} if exists $preference{allowPrints};
	$allowUserTheme = $preference{allowUserTheme} if exists $preference{allowUserTheme};
	$commentAbuserFilter = $preference{commentAbuserFilter} if exists $preference{commentAbuserFilter};
	$albumIconName = $preference{albumIconName} if exists $preference{albumIconName};
	$pathToJpegTran = $preference{pathToJpegTran} if exists $preference{pathToJpegTran};
	$idscgi = $preference{idsCGI} if exists $preference{idsCGI};
	$imageCache = $preference{imageCache} if exists $preference{imageCache};
	$sort = $preference{sortMethod} if exists $preference{sortMethod};
	$maxDisplayedComments = $preference{maxDisplayedComments} if exists $preference{maxDisplayedComments};
	$localization = $preference{localization} if exists $preference{localization};
	$theme = $preference{theme} if exists $preference{theme};
	$embeddedFilter = $preference{embeddedFilter} if exists $preference{embeddedFilter};
	$fileTypes = $preference{fileTypes} if exists $preference{fileTypes};
	$collectstats = $preference{collectstats} if exists $preference{collectstats};

	$fileTypes =~ s/\.//g;
	@fileTypes = split(/ /, $fileTypes);

	my $ppath = './';
	if ($prefsFile =~ /\A..\//) {
		$ppath = '../';
	}
	findThemes($ppath.'themes/');
	my $foundTheme = 'n';
	foreach my $availableTheme (@availableThemes) {
		next unless $availableTheme eq $theme;
		$foundTheme = 'y';
	}
	unless ($foundTheme eq 'y') {
		warn "Theme \"$theme\" not found. Reverting to default.";
		$theme='Sharp Grey';
	}
	findLocalizations($ppath.'localizations/');
	checkLocalization();
}

# Should this file be displayed by IDS?
sub displayableItem {
	my ($fileToCheck) = shift(@_);
	$fileToCheck =~ /\.(\w+)\Z/;
	my $fileExtension = $1;
	foreach my $filetype (@fileTypes) {
		if ($fileExtension =~ /\A$filetype\Z/i) {
			return 1;
		}
	}
	return 0;
}

# Confirms that the chosen language file exists
sub checkLocalization {
	my $foundLang = 'n';
	foreach my $availableLang (@availableLocalizations) {
		next unless $availableLang eq $localization;
		$foundLang = 'y';
	}
	unless ($foundLang eq 'y') {
		warn "Localization \"$localization\" not found. Reverting to default.";
		$localization='English';
	}
}

# Confirms that the chosen theme exists
sub checkTheme {
	my $foundTheme = 'n';
	foreach my $availableTheme (@availableThemes) {
		next unless $availableTheme eq $theme;
		$foundTheme = 'y';
	}
	unless ($foundTheme eq 'y') {
		warn "Theme \"$theme\" not found. Reverting to default.";
		$theme='Sharp Grey';
	}
}

# Reads in an ids localization file
sub readLocalization {
	my ($localizationFile) = shift(@_);
	open (LANG,"$localizationFile") || bail ("can't open localization file \"$localizationFile\": ($!)");
	while (<LANG>) {
		next if $_ =~ /^#|^\n/; #skip comments and blank lines
		chomp $_;
		my($tagtitle, $tagvalue) = split(/:/, $_);
		$tagvalue =~ s/\A"|"\Z//g;
		$localization{$tagtitle} = $tagvalue;
	}
	close (LANG) || bail ("can't close localization file: ($!)");
}

# Produces and displays an HTML error message
sub bail {
	my ($error) = shift(@_);
	my ($ppath) = shift(@_);

	my($newLogEntry) = $query->self_url."\nError: $error";
	appendLogFile($ppath."$logDir/error.txt", $newLogEntry);

	readLocalization($ppath."localizations/".$localization.".txt");
	print $query->header;
	print '	<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.0 Transitional//EN" "http://www.w3.org/TR/REC-html40/loose.dtd">
	  <html>
		<head>
		  <title>'.$localization{'error-label'}.'</title>
		  <style type="text/css"><!--
		  .smallgreytext { color: #808080; font-size: 9pt; font-family: Verdana, "Futura Book", Helvetica }
		  .text { color: #ffffff; font-weight: 600; font-size: 18pt; font-family: Verdana, "Futura Book", Helvetica }
		  .redtext { color: #8b0000 }-->
		  </style>
		</head>
		<body bgcolor="aaaaaa" link="#8b0000" vlink="#8b0000" text="black">
		  <br /><br /><br /><br /><br /><br />
		  <p>
		  <table border="0" width="600" align="center">
			<tr><td>
			  <table border="0" cellpadding="0" cellspacing="0" width="400" bgcolor="black" align="center">
				<tr><td>
				  <table border="0" cellpadding="0" cellspacing="1" width="400">
					<tr><td align="center" valign="middle" bgcolor="#8b0000">
					  <table width="300"><tr><td><h2><span class="text">'.$localization{'error-label'}.'</span></h2></td></tr></table>
					</td></tr>
					<tr><td bgcolor="#ffffff">
					  <table border="0" cellpadding="5" cellspacing="2" width="100%">
						<tr><td>
						  <div class="smallgreytext"><p>'.$localization{'error-text1'}.'</p><p><span class="redtext">"'.$error.'"</span></p><p>'.$localization{'error-text2'}.'</p></div>
						  <div class="smallgreytext" align="center"><p><a href="'.$ppath.$idscgi.'">&lt; '.$localization{'album-mainPageLink'}.'</a></p></div>
						</td></tr>
					  </table>
					</td></tr>
				  </table>
				</td></tr>
			  </table>
			</td></tr>
		  </table>
		</body>
	  </html>';
	exit;
}

# Displays an easily human-readable date and/or time, for example, 
# "18:58:46 on Oct. 30, 2000".
sub prettyTime {
	my($time) = shift(@_);
	my($timeFunction) = shift(@_);
	my($sec,$min,$hour,$mday,$mon,$year) = localtime($time);
	my(@MoY) = ('Jan.','Feb.','Mar.','Apr.','May','Jun.','Jul.','Aug.','Sep.','Oct.','Nov.','Dec.');
	$year += 1900; #Y2K compliance!
	if ($hour < 10) {$hour = "0".$hour;}
	if ($min < 10) {$min = "0".$min;}
	if ($sec < 10) {$sec = "0".$sec;}
	$mon = $MoY[$mon];
	$timeFunction='' unless defined $timeFunction;

	if ($timeFunction eq 'date') {
		my ($dateNTime) = "$mon $mday, $year";
		return $dateNTime;
	} elsif ($timeFunction eq 'time') {
		my ($dateNTime) = "$hour:$min:$sec";
		return $dateNTime;
	} else {
		my ($dateNTime) = "$mon $mday, $year $hour:$min:$sec";
		return $dateNTime;
	}
}

# Returns the path and name to a resized image.
sub filenameToDisplayName($$) {
	my $imageName = shift(@_);
	my $maxDimension = shift(@_);
	my ($base,$path,$type) = fileparse($imageName, '\.[^.]+\z');
	$path =~ s/\A\.\///;
	$path =~ s/\A[\.\.\/]*albums/$imageCache/;
	my($newDisplayName) = $path . $base . '_disp' . $maxDimension . '.jpg'; # what the resized image is named
	$newDisplayName =~ s/\/{2,}/\//g;
	return $newDisplayName;
}

sub generatePrevNext($$$$@) {
	my $albumName = shift(@_);
	my $imgName = shift(@_);
	my $title = shift(@_);
	my $style = shift(@_);
	my $ppath = shift(@_);

	$ppath = '' unless defined $ppath;
	my($base,$path,$type) = fileparse($imgName);
	$base = '' unless defined $base;
	$type = '' unless defined $type;
	my($previewName) = filenameToDisplayName("$albumName/$imgName", $previewMaxDimension);
	createDisplayImage($previewMaxDimension, $ppath, $previewName, $ppath."albums/$albumName/$imgName");
	my($prettyImageTitle) = $base;
	$prettyImageTitle =~ s/\#\d+_//g;
	$prettyImageTitle =~ s/\.[^.]+\Z//;
	$prettyImageTitle =~ s/_/ /g;
	my($xSize, $ySize) = getImageDimensions($ppath."image-cache/$previewName");
	my($previewHTML);
	unless ($style eq 'text') {
		$previewHTML = "<a href=\"".$idscgi.'?mode='.($ppath eq '../' ? 'edit' : '').'image&amp;'.($ppath eq '../' ? 'image=' : 'album=');
		$previewHTML .= encodeSpecialChars($albumName).($ppath eq '../' ? '/' : "&amp;image=");
		$previewHTML .= encodeSpecialChars($base.$type);
		$previewHTML .= "\">$title<br />\n<img src=\"";
		$previewHTML .= encodeSpecialChars($ppath."image-cache/".$previewName)."\" border=\"0\" ";
		$previewHTML .="width=\"$xSize\" "  if defined $xSize && $xSize;
		$previewHTML .="height=\"$ySize\" " if defined $ySize && $ySize;
		return "$previewHTML alt=\"[$title]\" /><br />\n$prettyImageTitle</a>";
	}
	return "<a href=\"$idscgi?mode=".($ppath eq '../' ? 'edit' : '')."image&amp;album=".encodeSpecialChars($albumName)."&amp;image=".encodeSpecialChars($base.$type)."\">$title</a>";
}

# Resizes an image and saves the result in the image-cache.
sub createDisplayImage($$@) {
	my $maxDimension = shift(@_);
	return unless(($maxDimension == $previewMaxDimension) || ($maxDimension == 350) || ($maxDimension == 512) || ($maxDimension == 640) || ($maxDimension == 800) || ($maxDimension == 1024) || ($maxDimension == 1600)); # avoid DOS attacks
	my $ppath=shift;
	my($imageToScale) = Image::Magick->new;

	foreach my $itemToDisplay (@_) {
		next if $itemToDisplay eq '';
		next if (-d $itemToDisplay); #this is a directory
		next unless ($itemToDisplay =~ /\.jpg\Z|\.jpeg\Z|\.gif\Z|\.png\Z|\.tif\Z/i); #this is a supported image filetype
		next if ($itemToDisplay =~ /_disp\d*\.jpg\Z/i); #this is a resized file
		my($newDisplayName) = filenameToDisplayName($itemToDisplay, $maxDimension);
		my($pathToCacheDir) = $newDisplayName;
		$pathToCacheDir =~ s/(.+)\/[^\/]+\Z//;
		$pathToCacheDir = $1;

		next if $pathToCacheDir eq '';
		unless (-d $pathToCacheDir) {
			mkpath($pathToCacheDir, 0, 0755) || die "Couldn't create path \"$pathToCacheDir\": $!";
			warn "Created path \"$pathToCacheDir\"";
		}

		# skip display file generation if a display file exists and is newer than image
		if (-e $newDisplayName) {
			next if ((-M $itemToDisplay) > (-M $newDisplayName));
		}

		$itemToDisplay =~ s/\/{2,}/\//g;
		my($x) = $imageToScale->Read($itemToDisplay); # read in the picture
		carp "$x" if "$x";

		$imageToScale->Set(quality=>$main::imageQuality);

		my($xSize, $ySize) = $imageToScale->Get('width', 'height'); # Get the picture's dimensions

		unless (($xSize <= $maxDimension) && ($ySize <= $maxDimension)) {  # image is less than maxsize and needs no rescaling
			# calculate dimensions of display image
			my($scaleFactor);
			my($displayX);
			my($displayY);
			if ($xSize > $ySize) {
				$scaleFactor = $maxDimension / $xSize;
				$displayX = $maxDimension;
				$displayY = int($ySize * $scaleFactor);
			} else {
				$scaleFactor = $maxDimension / $ySize;
				$displayY = $maxDimension;
				$displayX = int($xSize * $scaleFactor);
			}

			my $x = $imageToScale->Scale(width=>($displayX - (2 * $scaledImageBorderWidth)), height=>($displayY - (2 * $scaledImageBorderWidth))); #scale the image to the correct display size
			die "$x" if "$x";

			$x = $imageToScale->Border(color=>'black',width=>$scaledImageBorderWidth, height=>$scaledImageBorderWidth);
			die "$x" if "$x";

			if (($displayScaledIcon) eq 'y' && ($maxDimension eq $previewMaxDimension)) {
				my($overlayXSize, $overlayYSize) = $scaledOverlay->Get('width', 'height');
				$imageToScale->Composite(image=>$scaledOverlay,compose=>'over',geometry=>("+".($displayX - ($overlayXSize + $scaledImageBorderWidth))."+".($displayY - ($overlayYSize + $scaledImageBorderWidth)))); #overlay the scaled icon
			}

			$x = $imageToScale->Write($newDisplayName); #write out the thumbnail image file in JPEG format
			die "$x" if "$x";
		}
		undef $imageToScale;
	}
}

# Generates custom album previews from the first image in the album
sub generateAlbumPreview {
	my $AlbumName = shift(@_);
	my $imageForPreview = shift(@_);
	my $ppath = '';
	if ($AlbumName =~ /\A\.\.\//) {
		$ppath = '../';
	}

	my ($imagepreviewdir) = $AlbumName;

	$imagepreviewdir =~ s/[\.\.\/]*albums\//$albumData\//;
	my $previewNameTmp = $ppath."$imagepreviewdir/$theme.$albumIconName";
	return ($previewNameTmp) if (-e $previewNameTmp);

	my $albumfile = "$imagepreviewdir/album_image.txt";

	if ($imageForPreview ne '') {
		$imageForPreview = $ppath."albums/$AlbumName/$imageForPreview";
	} else {
		my $savedAlbumImage = openAlbumImage("$imagepreviewdir/");
		$imageForPreview = $ppath."albums" . $savedAlbumImage if ($savedAlbumImage ne '');
	}

	unless (-e "$imageForPreview") {
		@FilesToPreview = {};
		find (\&findImagesToPreview, "$AlbumName/");

		if ($#FilesToPreview > 0) {
			#pick a random image to use as the album's icon
			$imageForPreview = @FilesToPreview[int(rand($#FilesToPreview)) + 1];			

			my $imageForPreviewTmp = $imageForPreview;
			$imageForPreviewTmp =~ s/[..\/]*albums//;
			$imageForPreviewTmp =~ s/[..\/]*$albumData//;

			if (-e $ppath.'albums'.$imageForPreviewTmp) {
				writeItemDesc($albumfile, $imageForPreviewTmp);
			} else {
				croak "Unexpected error picking random album icon. (".$ppath.'albums'.$imageForPreviewTmp.")";
			}
		}
	}

	if (!defined $imageForPreview || $imageForPreview eq '' || -d "$imageForPreview" ) {
		# no images are available, so use a generic album icon
		my ($pathToIcon);
		if (-e $ppath."themes/$theme/images/albumicon.png") {
			$pathToIcon = $ppath."themes/$theme/images/albumicon.png";
		} else {
			$pathToIcon = $ppath."site-images/album_icon.png";
		}
		return ($pathToIcon);
	}

	$AlbumName =~ s/\balbums\///; # trims off 'albums/' from the filepath provided by glob.
	$AlbumName =~ s/\/\Z//;# trims off the trailing slash from the filepath provided by glob.
	$AlbumName =~ s/\.\.\///;

	my $previewName = "$albumData/$AlbumName/$theme.$albumIconName";

	unless (-e "$albumData/$AlbumName/") {
		# warn "Creating path \"$albumData/$AlbumName/\"";
		mkpath("$albumData/$AlbumName/", 0, 0755) || die "Couldn't create path \"$albumData/$AlbumName/\": $!";
	}

	my $background = Image::Magick->new;
	my $foreground = Image::Magick->new;
	my($x);

	my $pathToBackground;
	if (-e $ppath . "themes/$theme/images/albumbackground.png") {
		($pathToBackground) = $ppath."themes/$theme/images/albumbackground.png";
	} else {
		($pathToBackground) = $ppath."site-images/albumbackground.png";
	}

	$x = $background->Read("$pathToBackground"); # read in the picture
		die "$x" if "$x";
	$x = $foreground->Read("$imageForPreview"); # read in the picture
		carp "$x" if "$x";

	my($xSize, $ySize) = $foreground->Get('width', 'height'); # Get the picture's dimensions

	#Return if ImageMagick is dying on the image we selected
	return unless (defined $ySize && $ySize && defined $xSize && $xSize);
	my ($scaleFactor, $displayX, $displayY);
	if ($xSize > $ySize) {
		$displayX = int($xSize * (76/$ySize));
		$displayY = 76;
		if ($displayX < 51) {
			$displayX = 51;
			$displayY = int($ySize * (51/$xSize));
		}
	} else {
		$displayX = 51;
		$displayY = int($ySize * (51/$xSize));
		if ($displayY < 76) {
			$displayX = int($xSize * (76/$ySize));
			$displayY = 76;
		}
	}
	$x = $foreground->Scale(width=>$displayX, height=>$displayY);
	die "$x" if "$x";

	my($leftedge) = ($displayX - 51);
	if ($leftedge > 0) {
		$leftedge = int($leftedge / 2);
	} else {
		$leftedge = 0;
	}

	my($topedge) = ($displayY - 76);
	if ($topedge > 0) {
		$topedge = int($topedge / 2);
	} else {
		$topedge = 0;
	}

	$x = $foreground->Crop(width=>51, height=>76, x=>$leftedge, y=>$topedge);
		die "$x" if "$x";
	$x = $background->Composite(compose=>'Copy', image=>$foreground, geometry=>('+5+19'));
		die "$AlbumName: $x" if "$x";

	$background->Set(quality=>$imageQuality);
	$background->Quantize(colors=>256, dither=>'False');

	$x = $background->Write($previewName);
		die "$AlbumName: $x" if "$x";

	undef $foreground;
	undef $background;
	return ("$previewName");
}

sub findImagesToPreview {
	if (($_ =~ /\.jpg\Z|\.jpeg\Z|\.gif\Z|\.png\Z|\.tif\Z/i) && ($_ !~ /\A\./)) {
		push (@FilesToPreview, $File::Find::name);
	}
}

sub findAlbumsToPreview {
	if (-d $_ && ($_ !~ /CVS/)) {
		push (@AlbumsToPreview, $File::Find::name);
	}
}

sub writeItemDesc($$) {
	my $descFile = shift(@_);
	my $descriptionToWrite = shift(@_);

	my($base,$path,$type) = fileparse($descFile, '\.[^.]+\z');

	unless (-e "$path") {
		carp "Creating path \"$path\"";
		mkpath("$path", 0, 0755) || die "Couldn't create path \"$path\": $!";
	}

	eval {replace_file($descFile, sub {
		local *FH=shift;
		print FH $descriptionToWrite;
	})
	or die("Could not open the file description ($descFile)","$!");
	};
	die("Could not write a description ($descFile)", "$@") if $@;
}

sub findThemes {
	my $path = shift(@_);
	opendir THEMESDIR, $path || die ("can't open \"$path\" themes directory: ($!)");
	my @tempThemesDirs = grep !/^\.+/, readdir THEMESDIR;
	closedir THEMESDIR;

	undef @availableThemes;

	my $themeToCheck;
	foreach $themeToCheck (sort @tempThemesDirs) {
		next if ($themeToCheck =~ /CVS/); # exclude CVS entries
		next unless (-d $path.$themeToCheck);
		push @availableThemes, $themeToCheck; 
	}
}

sub findLocalizations {
	my $path = shift(@_);
	opendir LANGDIR, $path || die ("can't open \"$path\" localizations directory: ($!)");
	my @tempLocalizations = grep !/^\.+/, readdir LANGDIR;
	closedir LANGDIR;

	undef @availableLocalizations;

	my $langToCheck;
	foreach $langToCheck (sort @tempLocalizations) {
		next unless ($langToCheck =~ /.+\.txt\Z/);
		$langToCheck =~ s/\.txt//;
		push @availableLocalizations, $langToCheck;
	}

	if (-e 'localizations/mappings') {
		open (MAPPINGS,'localizations/mappings') || die ("can't open mappings file: ($!)");
		while (<MAPPINGS>) {
			next if $_ =~ /^#|^\n/; #skip comments and blank lines
			chomp $_;
			my($tagtitle, $tagvalue) = split(/:/, $_);
			$languageMappings{$tagtitle} = $tagvalue;
		}
		close (MAPPINGS) || die ("can't close mappings file: ($!)");
	}
}

# Opens an ids description file
sub openItemDesc {
	my $path = shift(@_);
	my $file;
	my ($description) = "";

	if ($path =~ /\/\Z/) {
		$file = "$path".'album_description.txt';
	} else {
		$file = "$path".'_desc.txt';
	}

	if (open (DESC, "$file")) {
		$description = (join '', <DESC>);
		close DESC;
	}
	return $description;
}

# Opens an ids album preview config
sub openAlbumImage {
	my $path = shift(@_);
	my $file;
	my ($imageForPreview) = "";

	if ($path =~ /\/\Z/) {
		$file = "$path".'album_image.txt';
	}

	if (open (DESC, "$file")) {
		$imageForPreview = (join '', <DESC>);
		close DESC;
	}
	return $imageForPreview;
}

sub fileSize {
	my($item) = shift(@_);
	return unless -e $item;
	my($filesize) = ((-s _) / 1024); #get the file's size in KB.
	if ($filesize > 1024) { # is it larger than a MB?
		$filesize = ($filesize / 1024);
		$filesize =~ s/(\d+\.\d)\d+/$1/;
		$filesize = $filesize." MB";
	} else {
		$filesize =~ s/(\d+)\.\d+/$1/;
		$filesize = $filesize." KB";
	}
	return $filesize;
}

# Gets the size of an image. Caches results
sub getImageDimensions {
	my $imageName = shift(@_);
	my ($infoFile) = getInfoFileName($imageName);
	my ($data, $width, $height, $size, $format, $status);

	$status = &isImageUpdated($imageName);

	if ($status == 1) {
		open(INFOFILE, "<$infoFile");
		$data = <INFOFILE>;
		close(INFOFILE);
		($width, $height, $size, $format) = split(/\|/, $data);
	} else {
		my $preview = Image::Magick->new;
		$preview->Read($imageName);
		($width, $height, $size, $format) = $preview->Get('base-columns','base-rows','filesize','format');

		if ($imageName =~ /_disp/) { # Don't write a file in the albums directory
			replace_file($infoFile,
				sub {
				local *FH = shift;
				print FH "$width\|$height\|$size\|$format\n";
			});
		}
	}
	return ($width, $height);
}

sub getInfoFileName {
	my $imageName = shift(@_);
	my($base,$path,$type) = fileparse($imageName, '\.[^.]+\z');
	return $path.$base.'.info';
}

# Checks to see if an image is newer than its info file
sub isImageUpdated {
	my $imageName = shift(@_);
	my ($infoFile) = getInfoFileName($imageName);
	my $status = 0;
	if (-e "$infoFile") {
		my $img_modTime = (stat($imageName))[9];
		my $info_modTime = (stat("$infoFile"))[9];
		if ($img_modTime < $info_modTime) {
			$status = 1;
		}
	}
	return($status);
}

# Initialize time variables
sub initTime {
	my($time) = time();
	my($sec,$min,$hour,$mday,$mon,$year) = localtime($time);
	$mon = $mon + 1; # Remember, perl starts with 0.
	$year += 1900; #Y2K compliance!
	if ($hour < 10) {$hour = "0".$hour;}
	if ($min < 10) {$min = "0".$min;}
	if ($sec < 10) {$sec = "0".$sec;}
	if ($mon < 10) {$mon = "0".$mon;}
	if ($mday < 10) {$mday = "0".$mday;}
	if ($year < 10) {$year = "0".$year;}
	my($currentDate) = "$mon\/$mday\/$year";
	my($currentTime) = "$hour:$min:$sec";
	return ($currentDate, $currentTime);
}

sub openTemplate {
	#opens an html template file
	my $File=shift;
	my $Path='';
	$Path = shift if scalar @_;
	open (TEMPLATE,$Path."themes/$theme/templates/$File.html") ||
		die ("cannot open template \"themes/$theme/templates/$File.html\" for reading: ($!)");
		$pageContent = join '', <TEMPLATE>;
	close (TEMPLATE) || die ("can't close template: ($!)");
}

# Reads in page/image hits from a file (sitestats)
sub readStats {
	return unless ( $collectstats eq 'y' );
	my ($statsFile) = ("$albumData/statsfile");
	return unless (-e $statsFile);
	my($hitfile, $hittype, $hitcounter);
	open (STATS,$statsFile) || die ("can't open Stats \"$statsFile\": ($!)");
	while (<STATS>) {
		my $rec = {};
		next if $_ =~ /^#|^\n/; #skip comments and blank lines
		chomp $_;
		($hitfile, $hittype, $hitcounter) = split(/\t/, $_);
		$rec->{FILE} = $hitfile;
		$rec->{TYPE} = $hittype;
		$rec->{COUNTER} = $hitcounter;
		push @stats, $rec;
	}
	close (STATS) || die ("can't close Stats: ($!)");
}

sub writeStats {
	return unless ( $collectstats eq 'y' );
	my ($statsFile) = ("$albumData/statsfile");
	open (STATS,">$statsFile") || die ("can't open stats \"$statsFile\": ($!)");
	my $i;
	my $key;
	for $i ( 0 .. $#stats ) {
		for $key ( "FILE" , "TYPE" , "COUNTER" ) {
			print STATS "$stats[$i]{$key}\t";
		}
		print STATS "\n";
	}
	close (STATS) || die ("can't close stats file: ($!)");
}

sub addStats($$) {
	return unless ( $collectstats eq 'y' );
	my $statName = shift(@_);
	my $statType = shift(@_);
	my ($i,$key);
	my $recnum = "NOTFOUND";
	$statName =~ s/^\/\.//;
	for $i ( 0 .. $#stats ) {
		if ($stats[$i]->{FILE} eq $statName) {
			if ($stats[$i]->{TYPE} eq $statType) {
				$recnum = $i;
				$stats[$i]->{COUNTER} ++;
			}
		}
	}
	if ($recnum eq "NOTFOUND") {
		my $rec = {};
		$rec->{FILE} = $statName;
		$rec->{TYPE} = $statType;
		$rec->{COUNTER} = 1;
		push @stats, $rec;
	}
}

sub processVarTags {
	# Prepare the HTML needed to create a searchbox 
	$searchBox = '<form action="' . $idscgi . '" method="get"><input type="hidden" value="search" name="mode" /><input type="text" name="searchstring" size="24" value="' . $searchString . '" /><br /><input type="submit" value="&nbsp;'.$localization{'site-searchButton'}.'&nbsp;" /></form>';

	# remove relative site-path and ids_style-path from template
	#$pageContent =~ s/\=\"\.\.\/[\.\/]*(site-)/\=\"$1/sg
	#	if defined $pageContent && ($commentContent ne '');
	#$pageContent =~ s/\=\"\.\.\/[\.\/]*(ids_style)/\=\"$1/sg
	#	unless (($adminContent ne '') || ($commentContent ne ''));

	# Replaces variable tags from the template with content.
	# <!tag> and comment style <!-- tag --> are found
	# use /sg , so tag is replaced all times

	#  first replace news and desc, so they can also contain var tags
	#
	$sitenews =~ s/.*<body.*?>(.*)<\/body.*/$1/is;
	$description =~ s/.*<body.*?>(.*?)<\/body.*/$1/is
		if defined $description;
	return unless defined $pageContent;
	$pageContent =~ s/<![- ]+admincontent[- ]*>/$adminContent/sg
		if defined $adminContent;
	$pageContent =~ s/<![- ]+sitenews[- ]*>/$sitenews/sg;
	$pageContent =~ s/<![- ]+description[- ]*>/$description/sg
		if defined $description;
	$pageContent =~ s/<![- ]+lastmodified[- ]*>/$lastModified/sg;
	$pageContent =~ s/<![- ]+albumlist[- ]*>/$home/sg if defined $home;
	$pageContent =~ s/<![- ]+albumlistsingle[- ]*>/$homesingle/sg if defined $homesingle;
	$pageContent =~ s/<![- ]+albumtitle[- ]*>/$albumtitle/sg if defined $albumtitle;
	$pageContent =~ s/\|\|albumtitle\|\|/$albumtitle/sg if defined $albumtitle;
	$pageContent =~ s/<![- ]+footer[- ]*>/$footer/sg if defined $footer;
	$pageContent =~ s/<![- ]+albumitems[- ]*>/$albumitems/sg;
	$pageContent =~ s/<![- ]*totalpictures[- ]*>/$totalitems/sg;	
	$pageContent =~ s/<![- ]*imagetitle[- ]*>/$imagetitle/sg;
	$pageContent =~ s/\|\|imagetitle\|\|/$imagetitle/sg;
	$pageContent =~ s/<![- ]*image[- ]*>/$image/sg if defined $image;
	$pageContent =~ s/<![- ]*prevthumb[- ]*>/$prevthumb/sg
		if defined $prevthumb;
	$pageContent =~ s/<![- ]*nextthumb[- ]*>/$nextthumb/sg
		if defined $nextthumb;
	$pageContent =~ s/<![- ]*prevtextthumb[- ]*>/$prevtextthumb/sg
		if defined $prevtextthumb;
	$pageContent =~ s/<![- ]*nexttextthumb[- ]*>/$nexttextthumb/sg
		if defined $nexttextthumb;
	$pageContent =~ s/<![- ]*previousalbum[- ]*>/$previousalbum/sg
		if defined $previousalbum;
	$pageContent =~ s/<![- ]*pictureinfo[- ]*>/$pictureinfo/sg
		if defined $pictureinfo;
	$pageContent =~ s/<![- ]*caminfo[- ]*>/$caminfo/sg
		if defined $caminfo;
	$pageContent =~ s/<![- ]*caminfo2[- ]*>/$caminfo2/sg
		if defined $caminfo2;
	$pageContent =~ s/<![- ]*imageresizer[- ]*>/$imageResizer/sg
		if defined $imageResizer;
	$pageContent =~ s/<![- ]*searchresults[- ]*>/$searchResults/sg
		if defined $searchResults;
	$pageContent =~ s/<![- ]*searchstring[- ]*>/$searchString/sg
		if defined $searchString;
	$pageContent =~ s/<![- ]*searchbox[- ]*>/$searchBox/sg
		if defined $searchBox;
	$pageContent =~ s/\|\|siteTitle\|\|/$siteTitle/sg
		if defined $siteTitle;
	$pageContent =~ s/<![- ]*siteHeader[- ]*>/$siteHeader/sg
		if defined $siteHeader;
	$pageContent =~ s/<![- ]*siteFooter[- ]*>/$siteFooter/sg
		if defined $siteFooter;
	$pageContent =~ s/<![- ]*orderprintsform[- ]*>/$orderPrintsForm/sg
		if defined $orderPrintsForm;
	$pageContent =~ s/<![- ]*sortmethod[- ]*>/$sortMethod/sg
		if defined $sortMethod;
	$pageContent =~ s/\|\|embeddedFilter\|\|/$embeddedFilter/sg
		if defined $embeddedFilter;	
	$pageContent =~ s/<![- ]*layers1[- ]*>/$Layers1/sg if defined $Layers1;
	$pageContent =~ s/<![- ]*layers2[- ]*>/$Layers2/sg if defined $Layers2;
	$pageContent =~ s/<![- ]*commentcontent[- ]*>/$commentContent/sg;
	my($commentViewer) = '<a href="postcomment/commentviewer.cgi">'.$localization{'home-commentLink'}.'</a>';
	$pageContent =~ s/<![- ]*commentviewer[- ]*>/$commentViewer/sg if ($guestComments eq 'y');
	$pageContent =~ s/<![- ]*homealbumlabel[- ]*>/$localization{'home-albumLabel'}/sg;
	$pageContent =~ s/<![- ]*homenewslabel[- ]*>/$localization{'home-newsLabel'}/sg;
	$pageContent =~ s/<![- ]*imagecomments[- ]*>/$localization{'image-comments'}/sg;
	$pageContent =~ s/<![- ]*imageshutterfly[- ]*>/$localization{'image-shutterfly'}/sg;
	$pageContent =~ s/\|\|searchlabel\|\|/$localization{'search-label'}/sg;
	$pageContent =~ s/<![- ]*searchlabel[- ]*>/$localization{'search-label'}/sg;
	$pageContent =~ s/<![- ]*searchtext[- ]*>/$localization{'search-text'}/sg;
	$pageContent =~ s/\|\|commentvlabel\|\|/$localization{'commentviewer-label'}/sg;
	$pageContent =~ s/<![- ]*commentvlabel[- ]*>/$localization{'commentviewer-label'}/sg;
	$pageContent =~ s/\|\|commentplabel\|\|/$localization{'commentposter-label'}/sg;
	$pageContent =~ s/<![- ]*commentplabel[- ]*>/$localization{'commentposter-label'}/sg;
	$pageContent =~ s/<![- ]*languagemenu[- ]*>/$languageMenu/sg;
	unless ($allowUserTheme eq 'n') {
		$pageContent =~ s/<![- ]*thememenu[- ]*>/$themeMenu/sg;
	}
	$pageContent =~ s/\|\|textlanguage\|\|/$localization{'site-language'}/sg;
	$pageContent =~ s/\|\|textencoding\|\|/$localization{'site-encoding'}/sg;
}

sub renderPage {
	# Spits out a page of HTML.
	my $cookiePath = $query->url(-absolute=>1);
	$cookiePath =~ s/$idscgi\Z|postcomment\/\w+\.\w+\Z//;

	my $cookie;
	if ($adminContent eq '') {
		$cookie = $query->cookie(-name=>'IDS_site_prefs',
					 -value=>"$sort||$maxDimension||$localization||$theme",
					 -path=>$cookiePath,
					 -expires=>'+1M'); #expires in 1 month
	}
	print $query->header(-type=>'text/html',
			     -expires=>'now',
			     -cookie=>$cookie);
	print $pageContent;
}
