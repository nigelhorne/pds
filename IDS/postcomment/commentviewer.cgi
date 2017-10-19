#!/usr/bin/perl
#
#########################################################################
#
# Image Display System Comment Viewer   		 5/26/2001     
# 			John Moose			moosejc@muohio.edu
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


# initialization
require CGI;
use strict;
use File::Basename;
use File::Path;
use File::Find;
use Image::Magick;
use lib qw(../);
use idsShared;


readPreferences('../ids.conf');

$scaledOverlay->Read("../site-images/previewicon.png"); # read in the "scaled" icon to overlay on scaled images

$imageCache = "../$imageCache";
$albumData = "../$albumData";
$logDir = "../$logDir";
$idscgi = "../$idscgi";

my ($currentDate, $currentTime) = initTime();
my ($mode, $albumtocomment, $imagetocomment, $commentername, $newcomment);



if ($guestComments eq 'n') {
	$! = "";
	bail ($localization{'commentposter-errorDisabled'}."$!");
}

$query = new CGI;
my($cookieSort, $cookieMaxDimension, $cookieLocalization, $cookieTheme) = readCookie();

if ($cookieLocalization) {
	$localization = $cookieLocalization;
	checkLocalization();
}

readLocalization("../localizations/".$localization.".txt");

if ($allowUserTheme eq 'y') {
	if ($cookieTheme) {
		$theme = $cookieTheme;
		checkTheme();
	}
}

# Make footer
$footer = $localization{'site-footer'};
$footer =~ s/\%time/$currentTime/;
$footer =~ s/\%date/$currentDate/;
my $IDSVersion = "<a href=\"http://ids.sourceforge.net/\">IDS $VERSION</a>";
$footer =~ s/\%version/$IDSVersion/;

$previousalbum = "<a href=\"$idscgi\">&lt; ".$localization{'commentviewer-mainPageLink'}."</a>";

$mode = 'viewcomments';
viewcomments();
openTemplate('viewcomments','../');
processVarTags();
renderPage();





###########################################################
#Functions:

sub viewcomments {
	unless (-e "$logDir/comments.txt") {
		$commentContent = "<div class=\"commentv-results\"><i>Sorry, there are no logged comments.</i><br /><br /></div>";
		return;
	}
	open (COMMENTS, "$logDir/comments.txt") || die ("can't open comments log \"$logDir/comments.txt\": ($!)");
	my($commentLogContents) = join '', <COMMENTS>;
	close (COMMENTS) || die ("can't close comments: ($!)");
	
	my(@comments) = split (/_______________________/, $commentLogContents);
	
	$commentContent .= '<table width="400" border="0" cellpadding="5">';
	
	my($comment) = '';
	my($counter) = 0;
	foreach $comment (reverse @comments) {
		last if ($counter > ($maxDisplayedComments-1));
		chomp $comment;
		next if ($comment eq '');
		my($imageToDisplay) = $comment =~ /\nComment re: ([^\n]*)\n/;
		next unless (-e "../albums/$imageToDisplay");
		
		my($poster) = $comment =~ /\A\n[^\n]*\n[^\n]*\n([^\n]*)\n/;
		my($commentToDisplay) = $comment =~ /$poster\n(.*)\Z/s;
		my($commentDate) = $comment =~ /\A([^-]*)-/;
		
		
		createDisplayImage($previewMaxDimension, '', "../albums/$imageToDisplay");
		my($previewName) = &filenameToDisplayName("albums/$imageToDisplay", $previewMaxDimension);
		my($base,$path,$type) = fileparse("$imageToDisplay", '\.[^.]+\z');
		my($albumtodisplay) = $path;
		$albumtodisplay =~ s/\/\Z//;
		
		my($xSize, $ySize) = &getImageDimensions("$previewName");
		my($imageNameTrimmed) = $base;
		$imageNameTrimmed =~ s/\.(\S+)\Z//;
		my ($prettyImageTitle) = $base;
		$prettyImageTitle =~ s/\#\d+_//g;
		$prettyImageTitle =~ s/_/ /g;
		
		$commentContent .= '<tr>';
		unless ($counter == 0) {
			$commentContent .= '<td colspan="2"><hr noshade="noshade" size="1" width="200" /></td></tr><tr>';
		}
		$commentContent .= "<td align=\"center\" valign=\"middle\"><a href=\"".$idscgi."?mode=image&amp;album=".&encodeSpecialChars($albumtodisplay)."&amp;image=".&encodeSpecialChars($base.$type)."\"><img src=\"".&encodeSpecialChars($previewName)."\" border=\"0\" width=\"$xSize\" height=\"$ySize\" alt=\"[$base$type]\" /></a></td>\n";
		$commentContent .= '<td valign="top"><div class="commentv-results">'."<a href=\"".$idscgi."?mode=image&amp;album=".&encodeSpecialChars($albumtodisplay)."&amp;image=".&encodeSpecialChars($base.$type)."\">$prettyImageTitle</a>".'<p />'.$localization{'commentviewer-from'}.': '.$poster.'<br />'.$localization{'commentviewer-time'}.': '.$commentDate.'<br />'.$localization{'commentviewer-comment'}.': <i>'.$commentToDisplay.'</i></div></td></tr>';
		$counter ++;
	}
	if ($counter == 0) {
		$commentContent .= '<tr><td colspan="2"><div class="highlight">'.$localization{'commentviewer-noComments'}.'</div></td></tr>';
	} else {
		my $temp = $localization{'commentviewer-counter'};
		$temp =~ s/\%comments/$counter/;
		$temp =~ s/\%totalComments/$#comments/;
		$commentContent .= '<tr><td colspan="2"><div class="commentv-results">'.$temp.'</div></td></tr>';
	}
	$commentContent .= '</table>';
}
