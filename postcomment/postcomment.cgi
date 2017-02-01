#!/usr/bin/perl
#
#########################################################################
#
# Image Display System Comment Poster   		 7/26/2001     
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
use strict;
require CGI;
use File::Basename;
use File::Path;
use File::Find;
use Image::Magick;
use lib qw(../);
use idsShared;

readPreferences('../ids.conf');

$scaledOverlay->Read("../site-images/previewicon.png"); # read in the "scaled" icon to overlay on scaled images


$albumData = "../$albumData";
$logDir = "../$logDir";
	

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

if ($guestComments eq 'n') {
	$! = "";
	croak ($localization{'commentposter-errorDisabled'}."$!");
}


# Global variables:
my ($base,$path,$type) = fileparse($0, '\.[^.]+\z');
my $idscgi= $base . $type; # get name of this script
my ($currentDate, $currentTime) = initTime();
my ($mode, $albumtocomment, $imagetocomment, $commentername, $newcomment);


	
# Make footer
$footer = $localization{'site-footer'};
$footer =~ s/\%time/$currentTime/;
$footer =~ s/\%date/$currentDate/;
my $IDSVersion = "<a href=\"http://ids.sourceforge.net/\">IDS $VERSION</a>";
$footer =~ s/\%version/$IDSVersion/;

processData();

if ($commentAbuserFilter eq 'y') {
	# check to see if this user has been banned
	my($userIP) = $query->remote_host();
	open (BANNED, "./banned_ip.txt") || croak ("can't open banned users file \"banned_ip.txt\": ($!)");
	while (<BANNED>) {
		next if $_ =~ /^#|^\n/; #skip comments and blank lines
		chomp $_;
		if ($userIP eq $_) {
			$commentContent = $commentContent . '
				<div class="commentp-text">
				'.$localization{'commentposter-errorBanned'}.'
				<br />
				<br />
				</div>';
			openTemplate();
			processVarTags();
			renderPage();
			exit;
		}
	}
	close (BANNED) || croak ("can't close banned users file: ($!)");
}

if ($mode eq 'createcomment') {
	createcomment();
} elsif ($mode eq 'verifycomment') {
	verifycomment();
} elsif ($mode eq 'postcomment') {
	postcomment();	
} else {
	croak ("Sorry, invalid mode. $!");
}

openTemplate('postcomment', '../');
processVarTags();
renderPage();





###########################################################
#Functions:

sub processData {
	# Interprets any form variables passed to the script. Checks to make sure the input makes sense.
	#
	if ($query->param('mode')) {
		$mode = $query->param('mode');
		chomp $mode;
		croak ("Sorry, invalid mode specified.$!") unless ($mode =~ /createcomment|verifycomment|postcomment/);
	} else {
		croak ("Sorry, no mode specified.$!","../");
	}
	
	if ($mode eq 'createcomment') {
		$albumtocomment = $query->param('album') || croak ("Sorry, no album name was provided.$!");
		unless (-e "../albums/$albumtocomment") { # does this album exist?
			croak ("Sorry, the album \"../albums/$albumtocomment\" doesn't exist. $!");
		}
		if ($albumtocomment =~ /\.\./) { # hax0r protection...
			croak ("Sorry, invalid album name.$!");
		}
		
		$imagetocomment = $query->param('image') || croak ("Sorry, no image name was provided.$!");
		unless (-e "../albums/$albumtocomment/$imagetocomment") { # does this image exist?
			croak ("Sorry, the image \"../albums/$albumtocomment/$imagetocomment\" doesn't exist. $!");
		}
		
		$commentername = $query->param('commentername');
		$newcomment = $query->param('comment');
	}
	
	if (($mode eq 'verifycomment') || ($mode eq 'postcomment')) {
		$albumtocomment = $query->param('album') || croak ("Sorry, no album name was provided.$!");
		unless (-e "../albums/$albumtocomment") { # does this album exist?
			croak ("Sorry, the album \"../albums/$albumtocomment\" doesn't exist. $!");
		}
		if ($albumtocomment =~ /\.\./) { # hax0r protection...
			croak ("Sorry, invalid album name.$!");
		}
		
		$imagetocomment = $query->param('image') || croak ("Sorry, no image name was provided.$!");
		unless (-e "../albums/$albumtocomment/$imagetocomment") { # does this image exist?
			croak ("Sorry, the image \"../albums/$albumtocomment/$imagetocomment\" doesn't exist. $!");
		}
		
		$commentername = $query->param('commentername');
		$newcomment = $query->param('comment') || croak ("Sorry, no comment was provided.$!");
	}
}

sub createcomment {
	$commentContent = $commentContent . '
				<form action="'.$idscgi.'" method="post">
				<input type="hidden" value="'.$albumtocomment.'" name="album" />
				<input type="hidden" value="'.$imagetocomment.'" name="image" />
				<input type="hidden" value="verifycomment" name="mode" />
				<div align="center">
				<table width="300" border="0" cellpadding="5" cellspacing="0">
					<tr>
						<td colspan="2"><span class="commentp-text">'.$localization{'commentposter-post'}.'</span><br /><br /><div align="center"><img src="../'.
				filenameToDisplayName('../albums'.encodeSpecialChars($albumtocomment).'/'.encodeSpecialChars($imagetocomment), $previewMaxDimension).'" /></div></td>
					</tr>
					<tr>
						<td width="150"><span class="commentp-text">'.$localization{'commentposter-name'}.':</span></td><td><input type="text" name="commentername" size="20" maxlength="30" value="'.$commentername.'" /></td>
					</tr>
					<tr>
						<td width="150"><span class="commentp-text">'.$localization{'commentposter-IPaddress'}.':</span></td><td><span class="commentp-text">'.$query->remote_host().'</span></td>
					</tr>
					<tr>
						<td colspan="2"><span class="commentp-text">'.$localization{'commentposter-comment'}.':</span><br /><textarea name="comment" cols="60" rows="4" wrap="virtual">'.$newcomment.'</textarea></td>
					</tr>
				</table>
				<br /><br /><div align="right"><input type="submit" value="&nbsp;&nbsp;'.$localization{'commentposter-previewCommentButton'}.'&nbsp;&nbsp;" /></div>
				</div>
				</form>';
	my $temp = $localization{'commentposter-linkToImage'};
	$temp =~ s/\%imageName/\"$imagetocomment\"/;
	$commentContent = $commentContent . '<div class="commentp-text" align="center"><br /><a href="../index.cgi?mode=image&amp;album='.encodeSpecialChars($albumtocomment).'&amp;image='.encodeSpecialChars($imagetocomment).'">&lt; '.$temp.'</a></div>';
}

sub verifycomment {
	$newcomment =~ s/(<|\%\W*3\W*c|\&lt)\/?[^>]*(>|\%\W*3\W*e|\&gt)//mig; #strip out any HTML, even if the user enters the "<" and/or ">" in encoded form
	
	$newcomment =~ s/"/\&quot;/mig; #replace quotes with "&quot;"
	
	my($newcommenttemp) = $newcomment;
	my ($CR, $LF) = (chr(13), chr(10));
	$newcommenttemp =~ s/[\n|$CR|$LF]{2}/<br \/>/g; # replaces line feed and carriage return characters with <br />'s
	
	$commentContent = $commentContent . '
				<div align="center">
					<table width="300" border="0" cellpadding="5" cellspacing="0">
						<tr>
							<td><span class="commentp-text">'.$localization{'commentposter-verify'}.'</span><br /><hr noshade="noshade" size="1" width="100" /></td>
						</tr>
						<tr>
							<td><div class="commentp-text"><i>'.($commentername ne '' ? $commentername : $localization{'commentposter-anon'}).'@'.$query->remote_host().':</i><br />'.$newcommenttemp.'</div></td>
						</tr>
					</table>
					<table width="300" border="0" cellpadding="5" cellspacing="0">
						<tr>
							<td>
								<form action="'.$idscgi.'" method="post">
								<input type="hidden" value="'.$albumtocomment.'" name="album" />
								<input type="hidden" value="'.$imagetocomment.'" name="image" />
								<input type="hidden" value="createcomment" name="mode" />
								<input type="hidden" value="'.$commentername.'" name="commentername" />
								<input type="hidden" value="'.$newcomment.'" name="comment" />
								<br /><br /><input type="submit" value="&nbsp;&nbsp;'.$localization{'commentposter-editCommentButton'}.'&nbsp;&nbsp;" />
								</form>
							</td>
							<td>
								<form action="'.$idscgi.'" method="get">
								<input type="hidden" value="'.$albumtocomment.'" name="album" />
								<input type="hidden" value="'.$imagetocomment.'" name="image" />
								<input type="hidden" value="postcomment" name="mode" />
								<input type="hidden" value="'.$commentername.'" name="commentername" />
								<input type="hidden" value="'.$newcomment.'" name="comment" />
								<br /><br /><input type="submit" value="&nbsp;&nbsp;'.$localization{'commentposter-postCommentButton'}.'&nbsp;&nbsp;" />
								</form>
							</td>
						</tr>
					</table>
				</div>';
	my $temp = $localization{'commentposter-linkToImage'};
	$temp =~ s/\%imageName/\"$imagetocomment\"/;
	$commentContent = $commentContent . '<br /><div class="commentp-text" align="center"><br /><a href="../index.cgi?mode=image&amp;album='.encodeSpecialChars($albumtocomment).'&amp;image='.encodeSpecialChars($imagetocomment).'">&lt; '.$temp.'</a></div>';
}

sub postcomment {
	$newcomment =~ s/<[\/]?[^>]*>//mig; #strip out any HTML
	$newcomment =~ s/"/\&quot;/mig; #replace quotes with "&quot;"
	
	my($newcommenttemp) = $newcomment;
	
	# Check for dirty words in comment, and ban user if present and filter enabled
	if ($commentAbuserFilter eq 'y') {
	    open (WORDS, "./words.txt") || warn ("can't open dirty words file \"words.txt\": ($!)");
	    my(@dirtyWordsTmp);
	    my(@dirtyWords);
		while (<WORDS>) {
			next if $_ =~ /^#|^\n/; #skip comments and blank lines
			chomp $_;
			push (@dirtyWordsTmp, lc($_));
		}
		close (WORDS) || croak ("can't close dirty words file: ($!)");
		
		my(%seen) = ();
		my($dirtyWord);
		foreach $dirtyWord (@dirtyWordsTmp) { #strip out duplicates
			push(@dirtyWords, $dirtyWord) unless $seen{$dirtyWord}++;
		}
		
		my($commentsTmp) = lc($commentername) . " " . lc($newcomment);
		$commentsTmp =~ s/[^a-z ]//g;
		my(@commentWordsTmp) = split /\s/, $commentsTmp;
		%seen = ();
		my($word);
		my(@commentWords);
		foreach $word (@commentWordsTmp) { #strip out duplicates
			push(@commentWords, $word) unless $seen{$word}++;
		}
		
		%seen = ();
		my($wordsFound) = 0;
		foreach $word (@dirtyWords, @commentWords) { #count duplicates
			 $wordsFound++ if $seen{$word}++;
		}
		
		if ($wordsFound gt 0) {
			open (BAN, '>>./banned_ip.txt') || warn "banned_ip.txt could not be opened";
				print BAN $query->remote_host() . "\n";
			close BAN; 
			my($newLogEntry) = "User at ".$query->remote_host()." has been banned for using dirty words.";
			appendLogFile("$logDir/admin.txt", $newLogEntry);
			# abort comment submission - this fella's locked out now!
			my $temp = $localization{'commentposter-linkToImage'};
			$temp =~ s/\%imageName/\"$imagetocomment\"/;
			$commentContent = $commentContent . '
				<div class="commentp-text">
				'.$localization{'commentposter-errorBanned1'}.'
				<br />
				<br />
				<div align="center"><a href="../index.cgi?mode=image&amp;album='.encodeSpecialChars($albumtocomment).'&amp;image='.encodeSpecialChars($imagetocomment).'">&lt; '.$temp.'"'.$imagetocomment.'"</a></div>
				</div>';
			return;
		}
	}

	my ($CR, $LF) = (chr(13), chr(10));
	$newcommenttemp =~ s/[\n|$CR|$LF]{2}/<br \/>/g; # replaces line feed and carriage return characters with <br />'s
	
	my($descFileTemp) = $albumtocomment.'/'.$imagetocomment;
	$descFileTemp =~ s/^\///;
	my($base,$path,$type) = fileparse($descFileTemp, '\.[^.]+\z');
	my ($descFileTemp) = "$albumData/$path$base";
	
	my($oldDescription) = openItemDesc($descFileTemp);
	
	$newcommenttemp = $oldDescription . ($oldDescription ne '' ? "\n".'<br /><hr noshade="noshade" size="1" width="100" />' : '') .'<i>'.($commentername ne '' ? $commentername : 'anonymous').'@'.$query->remote_host().' ('.$currentDate.' ' .$currentTime. '):</i><br />' . $newcommenttemp . "\n";
	
	writeItemDesc($descFileTemp.'_desc.txt', $newcommenttemp);
	
	my($newLogEntry) = "Comment re: $albumtocomment/$imagetocomment\n" . ($commentername ne '' ? $commentername : $localization{'commentposter-anon'}).'@'.$query->remote_host()."\n$newcomment";
	appendLogFile("$logDir/comments.txt", $newLogEntry);
	
	my $temp = $localization{'commentposter-linkToImage'};
	$temp =~ s/\%imageName/\"$imagetocomment\"/;
	$commentContent = $commentContent . '
				<div class="commentp-text">
				'.$localization{'commentposter-success'}.'
				<br />
				<br />
				<div align="center"><a href="../index.cgi?mode=image&amp;album='.encodeSpecialChars($albumtocomment).'&amp;image='.encodeSpecialChars($imagetocomment).'">&lt; '.$temp.'</a></div>
				</div>';
}
