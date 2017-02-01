#!/usr/bin/perl
#
#########################################################################
#
# Image Display System Admin 				6/7/2001     
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
use Image::Info qw(image_info);
use lib qw(..);
use idsShared;
use Carp;


$imageCache = "../$imageCache";
$albumData = "../$albumData";
$logDir = "../$logDir";

readPreferences('../ids.conf');
readLocalization("../localizations/".$localization.".txt");

$scaledOverlay->Read("../site-images/previewicon.png"); # read in the "scaled" icon to overlay on scaled images
  
$query = new CGI;
my($cookieSort, $cookieMaxDimension, $cookieLocalization, $cookieTheme) = readCookie();

if ($allowUserTheme eq 'y') {
	if ($cookieTheme) {
		$theme = $cookieTheme;
		checkTheme();
	}
}

my $preview = Image::Magick->new;
my $albumContent="";
my $filesInDir=0;
my $sizeTemp =0;
my $filesInCache=0;
my $sitenews='';
my ($lastVisit, $imagetoedit, $newalbumname, $newalbumdesc);
my ($newAlbumIconName);
my ($mode,  $startItem, $newimagedesc);
my ($itemtorename,  $newname, $extension, $uploadDest, $newsID);
my ($itemToRotate,  $degreesToRotate, $uploadFileName, $itemtodelete);
my ($newsToDelete,  $newsBody, $newsSubject, $prettyalbum, $result);
my ($newsDate, $previousalbumtemp, $imageCacheSize, $newMaxDimension);
my ($newPreviewMaxDimension, $newImagesPerRow, $newRowsPerPage);
my ($logSize, $descriptionToWrite, $previewName,$newSiteFooter,$newSiteHeader, $newAllowPrints, $allowUserTheme);
my ($newScaledImageBorderWidth, $newDisplayScaledIcon, $newImageQuality);
my ($newGuestComments, $newCommentAbuserFilter, $newSiteTitle, $newPathToJpegTran, @FilesToPreview);
    
# Global variables:
  
my ($base,$path,$type) = fileparse($0, '\.[^.]+\z');
$idscgi= $base . $type; # get name of this script
  
# Initialize time variables

  
my ($currentDate, $currentTime) = initTime();
  
processData();

if ($mode eq 'home') {
	generateHome();
} elsif ($mode eq 'viewalbum') {
	generateViewAlbum();
} elsif ($mode eq 'addalbum') {
	addAlbum();
} elsif ($mode eq 'addalbum2') {
	addAlbum2();
} elsif ($mode eq 'newalbumdesc') {
	newAlbumDesc();
} elsif ($mode eq 'editimage') {
	editImage();
} elsif ($mode eq 'newimagedesc') {
	newImageDesc();
} elsif ($mode eq 'renameimage') {
	renameImage();
} elsif ($mode eq 'renameimage') {
	renameImage();
} elsif ($mode eq 'newalbumiconfromimage') {
	newAlbumIconFromImage();
} elsif ($mode eq 'newalbumicon') {
	newAlbumIcon();
} elsif ($mode eq 'renamealbum') {
	renameAlbum();
} elsif ($mode eq 'renamealbum2') {
	renameAlbum2();
} elsif ($mode eq 'uploadfile') {
	uploadFile();
} elsif ($mode eq 'uploadfile2') {
	uploadFile2();
} elsif ($mode eq 'rotateimage') {
	rotateImage();
} elsif ($mode eq 'deleteimage') {
	deleteImage();
} elsif ($mode eq 'addnews') {
	addNews();
} elsif ($mode eq 'addnews2') {
	addNews2();
} elsif ($mode eq 'deletenews') {
	deleteNews();
} elsif ($mode eq 'clearimagecache') {
	clearimagecache();
} else {
	die ("Sorry, invalid mode.");
}

open (TEMPLATE,"./templates/admin.html") || die ("Cannot open \"./templates/admin.html\" template for reading: ($!)");
	$pageContent = join '', <TEMPLATE>;
close (TEMPLATE) || die ("can't close \"./templates/admin.html\" template: ($!)");
	
processVarTags();
renderPage();





###########################################################
#Functions:

sub updateHome {
   #This updates the static main index.
   #This can a be `slow' (ie, humans notice it) process, so we spawn it off
   #and forget about it.
   return if (my $pid=fork()) >1;
   replace_file("../index.html",
	sub {
	      local *FH=shift;
	      #Change our standard out to the index html file
	      my $OldFD;
	      $OldFD = dup(1) if $pid;
	      dup2(fileno(FH), 1);
	      system("cd ..;./index.cgi -n");
	      #Restore our standard out
	      dup2($OldFD, 1) if $pid;
	});
   #If we are a child process, exit
   exit(0) unless $pid < 0;
}

#A subroutine to extract the CGI data about renaming items.  It does some
#crude pattern checking to help taint check the variables.
sub getNewName($) {
	my $query=shift;
	my $itemtorename='';
	my $itemname = $query->param('itemtorename') || die ("Sorry, no item name was provided: $!");
	$itemtorename = $1 if $itemname =~ /([\w\d\s\-+=\[\].,\?`\/\\~!@#$%&*(){}:;"'\^]+)/i;
	unless ($itemtorename eq $itemname && -e "../albums$itemtorename") { # does this image exist?
		die ("Sorry, \"../albums$itemtorename\" doesn't exist: $!");
	}
	if ($itemtorename =~ /\.\./) { # hax0r protection...
		die ("Sorry, invalid image name: $!");
	}
		
	my $newname = $query->param('newname') || die ("Sorry, no new name was provided: $!");
	if ($newname) {
		$newname = $1 if $newname=~ /([\w\d\s\-+=\[\].,\?`~!@#$%&*(){}:;"'\^]+)/i;
		$newname =~ s/^[\.]+|\///g; # hax0r protection...
	}
		
	my $extension = $query->param('extension');
	if ($extension) {
		$extension= $1 if $extension=~/([\w\d\s\-+=\[\].,\?`~!@#$%&*(){}:;"'\^]+)/i;
		$extension =~ s/^[\.]+|\///g; # hax0r protection...
	}
	return($itemtorename, $newname, $extension);
}

sub processData {
	# Interprets any form variables passed to the script. Checks to make sure the input makes sense.
	#
	if ($query->param('mode')) {
		$mode = $query->param('mode');
		chomp $mode;
		unless ($mode =~ /viewalbum|addalbum|addalbum2|newalbumdesc|editimage|newimagedesc|renameimage|newalbumiconfromimage|newalbumicon|rotateimage|renamealbum|renamealbum2|uploadfile|uploadfile2|deleteimage|addnews|addnews2|deletenews|editprefs|editprefs2|clearimagecache/) {$mode = 'home';}
	} else {
		$mode = 'home';
	}
	
	if ($mode eq 'viewalbum' || $mode eq 'addalbum' || $mode eq 'renamealbum') {
	    getAlbumToDisplay('../');
  	}
  	
  	if ($mode eq 'addalbum2') {
	    getAlbumToDisplay('../');
		$newalbumname = $query->param('newalbumname') || die ("Sorry, no new album name was provided: $!");
  		$newalbumname =~ s/^[\.]+|\///g; # hax0r protection...
  	}
  	
  	if ($mode eq 'newalbumdesc') {
	    getAlbumToDisplay('../');
  		$newalbumdesc = $query->param('newalbumdesc');
  	}
  	
  	if ($mode eq 'editimage') {
		$imagetoedit = $query->param('image') || die ("Sorry, no image name was provided: $!");
  		unless (-e "../albums/$imagetoedit") { # does this image exist?
			die ("Sorry, \"../albums/$imagetoedit\" doesn't exist: $!");
  		}
  		if ($imagetoedit =~ /\.\./) { # hax0r protection...
			die ("Sorry, invalid image name: $!");
  		}
  		$imagetoedit = '/' . $imagetoedit;
	}
	
	if ($mode eq 'newimagedesc') {
		$imagetoedit = $query->param('image') || die ("Sorry, no image name was provided: $!");
  		unless (-e "../albums/$imagetoedit") { # does this image exist?
			die ("Sorry, \"../albums/$imagetoedit\" doesn't exist: $!");
  		}
  		if ($imagetoedit =~ /\.\./) { # hax0r protection...
			die ("Sorry, invalid image name: $!");
  		}
  		$imagetoedit = '/' . $imagetoedit;
		$newimagedesc = $query->param('newimagedesc');
	}
	
	if ($mode eq 'newalbumiconfromimage') {
		$imagetoedit = $query->param('image') || die ("Sorry, no image name was provided: $!");
  		unless (-e "../albums/$imagetoedit") { # does this image exist?
			die ("Sorry, \"../albums/$imagetoedit\" doesn't exist: $!");
  		}
  		if ($imagetoedit =~ /\.\./) { # hax0r protection...
			die ("Sorry, invalid image name: $!");
  		}
  		$imagetoedit = '/' . $imagetoedit;
	}
	
	if ($mode eq 'newalbumicon') {
		$albumtodisplay = $query->param('album') || die ("Sorry, no album name was provided: $!");
  		unless (-e "../albums$albumtodisplay") { # does this album exist?
			die ("Sorry, \"../albums$albumtodisplay\" doesn't exist: $!");
  		}
	}
	
	if ($mode eq 'renameimage') {
		($itemtorename, $newname, $extension) = getNewName($query);
  	}
  	
  	if ($mode eq 'rotateimage') {
		$itemToRotate = $query->param('itemtorotate') || die ("Sorry, no item name was provided: $!");
  		unless (-e "../albums$itemToRotate") { # does this image exist?
			die ("Sorry, \"../albums$itemToRotate\" doesn't exist: $!");
  		}
  		
		$degreesToRotate = $query->param('degrees') || die ("Sorry, no angle was provided: $!");
  	}
  	
  	if ($mode eq 'renamealbum2') {
		($itemtorename, $newname, $extension) = getNewName($query);
  	}
  	
  	if ($mode eq 'uploadfile') {
		$uploadDest = $query->param('uploaddest') || die ("Sorry, no destination was selected: $!");
  		unless (-e "../albums/$uploadDest") { # does this image exist?
			die ("Sorry, \"../albums/$uploadDest\" doesn't exist: $!");
  		}
  		
  		if ($uploadDest =~ /\.\./) { # hax0r protection...
			die ("Sorry, invalid destination name: $!");
  		}
  	}
  	
  	if ($mode eq 'uploadfile2') {
		$uploadFileName = $query->param('uploadfile') || die ("Sorry, no file was selected: $!");
  		
		$uploadDest = $query->param('uploaddest') || die ("Sorry, no destination was selected: $!");
  		unless (-e "../albums/$uploadDest") { # does this image exist?
			die ("Sorry, \"../albums/$uploadDest\" doesn't exist: $!");
  		}
  		
  		if ($uploadDest =~ /\.\./) { # hax0r protection...
			die ("Sorry, invalid destination name: $!");
  		}
  	}
  	
  	if ($mode eq 'deleteimage') {
		$itemtodelete = $query->param('itemtodelete') || die ("Sorry, no item name was provided: $!");
  		unless (-e "../albums/$itemtodelete") { # does this image exist?
			die ("Sorry, \"../albums/$itemtodelete\" doesn't exist: $!");
  		}
  		if ($itemtodelete =~ /\.\./) { # hax0r protection...
			die ("Sorry, invalid image name: $!");
  		}
  	}
	
	if ($mode eq 'addnews') {
		$newsID = $query->param('newsid');
		
		unless (($newsID =~ /\A\d{14}\Z/ ) || ($newsID eq '')) {
			die ("Sorry, invalid news item ID: $!");
  		}
  	}
  	
  	if ($mode eq 'addnews2') {
		$newsSubject = $query->param('newssubject') || die ("Sorry, no news subject was provided: $!");
		$newsBody = $query->param('newsmessage') || die ("Sorry, no news body was provided: $!");
  		
  		$newsID = $query->param('newsid');
  		
  		unless (($newsID =~ /\A\d{14}\Z/ ) || ($newsID eq '')) {
			die ("Sorry, invalid news item ID: $!");
  		}
		
		$newsSubject =~ s/::://g;
		$newsBody =~ s/::://g;
	}
	
	if ($mode eq 'deletenews') {
		$newsToDelete = $query->param('newstodelete') || die ("Sorry, no news item to delete was specified: $!");
	}
	
	if ($mode eq 'clearimagecache') {
		# placeholder
	}
	$query->delete_all();
}
 
sub findDirSize {
    return if /^\.{1,2}$/;
  	$filesInDir += 1;
	my($base,$path,$type) = fileparse($File::Find::name, '\.[^.]+\z');
	$base='' unless defined $base;
	$type='' unless defined $type;
	$sizeTemp += -s;
}
  
sub generateHome {
  	$albumtodisplay ='/';
  	$adminContent = '';
  	$filesInCache = 0;
	$filesInDir=0;
	$sizeTemp =0;
  	find (\&findDirSize, "$imageCache/");
	unless (!$filesInDir) {$filesInCache = $filesInDir;}
  	$imageCacheSize = $sizeTemp / 1024;
  	if ($imageCacheSize > 1024) { # is it larger than a MB?
		$imageCacheSize = ($imageCacheSize / 1024);
		$imageCacheSize =~ s/(\d+\.\d)\d+/$1/;
		$imageCacheSize = $imageCacheSize." MB";
	} else {
		$imageCacheSize =~ s/(\d+)\.\d+/$1/;
		$imageCacheSize = $imageCacheSize." KB";
	}
	
	$sizeTemp = 0;
	
	mkdir $logDir, 0777 unless -e $logDir;
	$filesInDir=0;
  	find (\&findDirSize, "$logDir/");
  	$logSize = $sizeTemp / 1024;
	if ($logSize > 1024) { # is it larger than a MB?
		$logSize = ($logSize / 1024);
		$logSize =~ s/(\d+\.\d)\d+/$1/;
		$logSize = $logSize." MB";
	} else {
		if (($logSize < 1) && ($logSize > 0)) {
			$logSize =~ s/(\d+)\.(\d)\d+/$1\.$2/;
		} else {
			$logSize =~ s/(\d+)\.\d+/$1/;
		}
		$logSize = $logSize." KB";
	}
	
	my($adminLogDate);
	my($commentLogDate);
	my($errorLogDate);
	
	if (-e "$logDir/admin.txt") {
		$adminLogDate = prettyTime((stat "$logDir/admin.txt")[9]);
	} else {
		$adminLogDate = "<i>no log found</i>";
	}
	
	if (-e "$logDir/comments.txt") {
		$commentLogDate = prettyTime((stat "$logDir/comments.txt")[9]);
	} else {
		$commentLogDate = "<i>no log found</i>";
	}
	
	if (-e "$logDir/error.txt") {
		$errorLogDate = prettyTime((stat "$logDir/error.txt")[9]);
	} else {
		$errorLogDate = "<i>no log found</i>";
	}
	
	$description = openItemDesc("$albumData/");
	
	$adminContent = '<table border="0" cellpadding="0" cellspacing="0" width="500" bgcolor="black" align="center">
						<tr><td>
						<table border="0" cellpadding="0" cellspacing="1" width="500">
							<tr>
								<td align="center" valign="middle" bgcolor="gray">
									<table width="400"><tr><td><h2><span class="text">albums</span></h2></td><td align="right"><span class="smalltext">'.$totalitems.'&nbsp;</span></td></tr></table>
								</td>
							</tr>
							<tr>
								<td bgcolor="white">
									<table border="0" cellpadding="5" cellspacing="1" width="100%">
										<tr>
											<td>
												<form action="'.$idscgi.'" method="post">
												<input type="hidden" value="/" name="album">
												<input type="hidden" value="newalbumdesc" name="mode">
												<span class="smallgreytext">Enter/edit a description of this site here. Use HTML if you wish.</span><p>
												<textarea name="newalbumdesc" cols="60" rows="4" wrap="virtual">'. $description .'</textarea><br>
												<div align="right"><input type="submit" value="&nbsp;&nbsp;Save Description&nbsp;&nbsp;"></div></form><br>
											</td>
										</tr>
										<tr>
											<td>' . "\n".generateAlbumView()."\n" . '
											</td>
										</tr>
										<tr>
											<td align="center"><span class="smallgreytext">| <a href="'.$idscgi."?mode=addalbum&amp;album=".&encodeSpecialChars($albumtodisplay).'">Add new album here</a> |</span>
											<br><br>
											</td>
										</tr>
									</table>
								</td>
							</tr>
							<tr>
								<td align="center" valign="middle" bgcolor="gray">
									<table width="400"><tr><td><h2><span class="text">news</span></h2></td></tr></table>
								</td>
							</tr>
							<tr>
								<td bgcolor="white">
									<table border="0" cellpadding="5" cellspacing="1" width="100%">
										<tr>
											<td>';
	openNewsDesc("../");
	$adminContent .= $sitenews;								
	$adminContent .= '
											</td>
										</tr>
										<tr>	
											<td align="center"><span class="smallgreytext">| <a href="'.$idscgi.'?mode=addnews">Add a news item</a> |</span>
											<br><br>
											</td>
										</tr>
									</table>
								</td>
							</tr>
							<tr>
								<td align="center" valign="middle" bgcolor="gray">
									<table width="400"><tr><td><h2><span class="text">preferences</span></h2></td></tr></table>
								</td>
							</tr>
							<tr>
								<td bgcolor="white">
									<table border="0" cellpadding="5" cellspacing="1" width="100%">
										<tr>
											<td>
												<table border="0" cellpadding="5" cellspacing="1" align="center" width="400">
													<tr>
														<td><span class="smallgreytext">Default image size</span></td><td><span class="smallgreytext">'.$maxDimension.' pixel'.($maxDimension eq 1 ? '' : 's').'</span></td>
													</tr>
													<tr>
														<td><span class="smallgreytext">Preview/thumbnail max dimension</span></td><td><span class="smallgreytext">'.$previewMaxDimension.' pixel'.($previewMaxDimension eq 1 ? '' : 's').'</span></td>
													</tr>
													<tr>
														<td><span class="smallgreytext">Images per row</span></td><td><span class="smallgreytext">'.$imagesPerRow.' image'.($imagesPerRow eq 1 ? '' : 's').'</span></td>
													</tr>
													<tr>
														<td><span class="smallgreytext">Rows per page</span></td><td><span class="smallgreytext">'.$rowsPerPage.' row'.($rowsPerPage eq 1 ? '' : 's').'</span></td>
													</tr>
													<tr>
														<td><span class="smallgreytext">Scaled image border width</span></td><td><span class="smallgreytext">'.$scaledImageBorderWidth.' pixel'.($scaledImageBorderWidth eq 1 ? '' : 's').'</span></td>
													</tr>
													<tr>
														<td><span class="smallgreytext">Display "thumbnail" corner icon?</span></td><td><span class="smallgreytext">'.($displayScaledIcon =~ /y/i ? 'Yes' : 'No').'</span></td>
													</tr>
													<tr>
														<td><span class="smallgreytext">Resized image quality</span></td><td><span class="smallgreytext">'.$imageQuality.'%</span></td>
													</tr>
													<tr>
														<td><span class="smallgreytext">Allow guest comments?</span></td><td><span class="smallgreytext">'.($guestComments =~ /y/i ? 'Yes' : 'No').'</span></td>
													</tr>
													<tr>
														<td colspan="2"><span class="smallgreytext"><br>* <i>Due to browser caching issues, changes may not be displayed until this page is reloaded.</i></span></td>
													</tr>
												</table>
											</td>
										</tr>
										<tr>
											<td align="center"><span class="smallgreytext">| <a href="./preferences.cgi">Edit IDS preferences</a> |</span>
											<br><br>
											</td>
										</tr>
									</table>
								</td>
							</tr>
							<tr>
								<td align="center" valign="middle" bgcolor="gray">
									<table width="400"><tr><td><h2><span class="text">image cache</span></h2></td></tr></table>
								</td>
							</tr>
							<tr>
								<td bgcolor="white">
									<table border="0" cellpadding="5" cellspacing="1" width="100%">
										<tr>
											<td>
												<table border="0" cellpadding="5" cellspacing="1" align="center" width="400">
													<tr>
														<td><span class="smallgreytext">Files and directories in cache</span></td><td><span class="smallgreytext">'. $filesInCache .'</span></td>
													</tr>
													<tr>
														<td><span class="smallgreytext">Cache size</span></td><td><span class="smallgreytext">'. $imageCacheSize .'</span></td>
													</tr>
												</table>
											</td>
										</tr>
										<tr>
											<td align="center"><span class="smallgreytext">| <a href="'.$idscgi.'?mode=clearimagecache">Clear image cache</a> |</span>
											<br><br>
											</td>
										</tr>
									</table>
								</td>
							</tr>
							<tr>
								<td align="center" valign="middle" bgcolor="gray">
									<table width="400"><tr><td><h2><span class="text">logs</span></h2></td></tr></table>
								</td>
							</tr>
							<tr>
								<td bgcolor="white">
									<table border="0" cellpadding="5" cellspacing="1" width="100%">
										<tr>
											<td align="center">
												<table border="0" cellpadding="5" cellspacing="1" align="center" width="400">
													<tr>
														<td><span class="smallgreytext">Admin log last modified</span></td><td><span class="smallgreytext">'. $adminLogDate .'</span></td>
													</tr>
													<tr>
														<td><span class="smallgreytext">Comment log last modified</span></td><td><span class="smallgreytext">'. $commentLogDate .'</span></td>
													</tr>
													<tr>
														<td><span class="smallgreytext">Error log last modified</span></td><td><span class="smallgreytext">'. $errorLogDate .'</span></td>
													</tr>
													<tr>
														<td><span class="smallgreytext">Total size of logs</span></td><td><span class="smallgreytext">'. $logSize .'</span></td>
													</tr>
												</table>
											
												<span class="smallgreytext"> | <a href="'.$logDir.'/">View IDS logs</a> | </span>
												<br><br>
											</td>
										</tr>
									</table>
								</td>
							</tr>
						</table>
						</td></tr>
					</table>';
	$previousalbum = '';
}

sub generateViewAlbum {
	$adminContent .= generateAlbumView();
	my($prettyAlbumName) = $albumtodisplay;
	$prettyAlbumName =~ s/([^\/]+)\/?$//; #trim off the directory path returned by glob
	$prettyAlbumName = $1;
	
	$description = openItemDesc("$albumData/$albumtodisplay/");
	
	my $previewName = $albumData.'/'.$albumtodisplay.'/'.$theme.'.'.$albumIconName;
	
	unless (-e $previewName) {
		$previewName = generateAlbumPreview("../albums$albumtodisplay");
	}
	if ($previewName eq '') {
		$previewName = '../site-images/album_icon.png';
	}
	my($xSize, $ySize) = &getImageDimensions("$previewName");
	my $albumIcon .= "<img src=\"".&encodeSpecialChars($previewName)."\" border=\"0\" ";
	$albumIcon .= "width=\"$xSize\" " if defined $xSize;
	$albumIcon.= "height=\"$ySize\" " if defined $ySize;
	$albumIcon .= "alt=\"[$prettyAlbumName]\">";
	
	$adminContent = '<table border="0" cellpadding="0" cellspacing="0" width="500" bgcolor="black" align="center">
						<tr><td>
						<table border="0" cellpadding="0" cellspacing="1" width="500">
							<tr>
								
								<td align="center" valign="middle" bgcolor="gray">
									<table width="400"><tr><td><h2><span class="text">'. $prettyAlbumName .'</span></h2></td><td><span class="smalltext">'.$totalitems.'&nbsp;</span></td></tr></table>
								</td>
							</tr>
							<tr>
								<td>
								<table border="0" cellpadding="0" cellspacing="0" width="500">
									<tr>
										<td colspan="3" bgcolor="white">
											<table border="0" cellpadding="5" cellspacing="1" width="100%">
												<tr>
													<td>
														<table align="center" cellpadding="0">
															<tr>
																<td width="100" valign="top" align="center">
																	'.$albumIcon.'<br>
																	<a href="'.$idscgi.'?mode=newalbumicon&album='.&encodeSpecialChars($albumtodisplay).'">random icon</a>
																</td>
																
																<td>
																	<form action="'.$idscgi.'" method="get">
																	<input type="hidden" value="'.$albumtodisplay.'" name="album">
																	<input type="hidden" value="newalbumdesc" name="mode">
																	<span class="smallgreytext">Enter/edit a description of the album "'. $prettyAlbumName .'" here. Use HTML if you wish.</span><p>
																	<textarea name="newalbumdesc" cols="40" rows="4" wrap="virtual">'. $description .'</textarea><br>
																	<div align="right"><input type="submit" value="&nbsp;&nbsp;Save Description&nbsp;&nbsp;"></div></form><br>
																</td>
															</tr>
														</table>
													</td>
												</tr>
											</table>
										</td>
									</tr>
									<tr>
										<td colspan="3" align="center" bgcolor="white"><span class="smallgreytext"><a href="'.$idscgi."?mode=uploadfile&amp;uploaddest=".&encodeSpecialChars($albumtodisplay).'">Upload a file here</a> | <a href="'.$idscgi."?mode=addalbum&amp;album=".&encodeSpecialChars($albumtodisplay).'">Add new album here</a> |  <a href="'.$idscgi."?mode=renamealbum&amp;album=".&encodeSpecialChars($albumtodisplay).'">Rename this album</a></span>
										<br>
										<br>
										<div class="smallgreytext">* Some changes may not be displayed correctly until this page is reloaded.</div>
										<br><br>
										</td>
									</tr>
									<tr>
										<td colspan="3" bgcolor="white">
											<table border="0" cellpadding="5" cellspacing="1" width="100%">
												<tr>
													<td>' . $adminContent . '
													</td>
												</tr>
											</table>
										</td>
									</tr>
									
								</table>
								</td>
							</tr>
						</table>
						</td></tr>
					</table>';
	
	
}

sub renameAlbum {
	my ($previousalbumtemp);
	
	if ($albumtodisplay =~ /\/.+/) {
		($previousalbumtemp, $albumtitle) = $albumtodisplay =~ /^\/(.+)/;
		$previousalbum = "<a href=\"".$idscgi."?mode=viewalbum&amp;album=".&encodeSpecialChars($previousalbumtemp)."\">&lt; back to album</a>";
	} else {
		($albumtitle) = $albumtodisplay =~ /([^\/]+)$/;
		$previousalbum = "<a href=\"".$idscgi."\">&lt; main page</a>";
	}
	
	my ($prettyalbum) = $albumtodisplay;
	$prettyalbum =~ s/([^\/]+)\/?$//; #trim off the directory path returned by glob
	$prettyalbum = $1;
	
	$adminContent = $adminContent . '<table border="0" cellpadding="0" cellspacing="0" width="400" bgcolor="black" align="center">
						<tr><td>
						<table border="0" cellpadding="0" cellspacing="1" width="400">
							<tr>
								
								<td align="center" valign="middle" bgcolor="gray">
									<table width="300"><tr><td><h2><span class="text">rename album</span></h2></td></tr></table>
								</td>
							</tr>
							<tr>
								<td bgcolor="white">
									<table border="0" cellpadding="5" cellspacing="1" width="100%">
										<tr>
											<td>
											<table align="center" cellpadding="5"><tr><td>
												<form action="'.$idscgi.'" method="post">
												<input type="hidden" value="'.$albumtodisplay.'" name="itemtorename">
												<input type="hidden" value="renamealbum2" name="mode">
												<div class="smallgreytext">Rename the album "'.$prettyalbum.'":<p>
												<input type="text" name="newname" size="24" maxlength="200" value="'.$prettyalbum.'"><br></div>
												<div align="right"><input type="submit" value="&nbsp;&nbsp;Rename&nbsp;&nbsp;"></div>
												</form>
											</td></tr></table>
											</td>
										</tr>
									</table>
								</td>
							</tr>
						</table>
						</td></tr>
					</table>';
}

sub addNews {
	if ($newsID ne '') {
		if (open (NEWS, "../site_news.txt")) {
			while (<NEWS>) {
				next if $_ =~ /^#|^\n/; #skip comments and blank lines
				chomp $_;
				next unless ($_ =~/\A$newsID/);
				($newsDate, $newsSubject, $newsBody) = split(/:::/, $_);
			}
			close (NEWS) || die ("can't close news file: ($!)");
		}
	}
	
	$previousalbum = "<a href=\"".$idscgi."\">&lt; back to main page</a>";
	$adminContent = $adminContent . '<table border="0" cellpadding="0" cellspacing="0" width="400" bgcolor="black" align="center">
						<tr><td>
						<table border="0" cellpadding="0" cellspacing="1" width="400">
							<tr>
								
								<td align="center" valign="middle" bgcolor="gray">
									<table width="300"><tr><td><h2><span class="text">add news item</span></h2></td></tr></table>
								</td>
							</tr>
							<tr>
								<td bgcolor="white">
									<table align="center" cellpadding="5">
										<tr>
											<td>
												<p><span class="smallgreytext">Please enter your news item here. You may use HTML tags if you wish. Linefeeds (RETURN or ENTER) will be converted to &lt;br&gt; tags</span></p>
												<form action="'.$idscgi.'" method="post">
												<input type="hidden" value="addnews2" name="mode">
												<input type="hidden" value="'.$newsDate.'" name="newsid">
												<table>
													<tr>
														<td valign="top">
															<span class="smallgreytext">Subject:</span>
														</td>
														<td>
															<input type="text" name="newssubject" size="36" maxlength="48" value="'. $newsSubject . '"><span class="smallgreytext">&nbsp;*optional</span>
														</td>
														</tr>
														<tr>
														<td valign="top">
															<span class="smallgreytext">Message:</span></td><td><textarea name="newsmessage" cols="60" rows="8" wrap="virtual">'. $newsBody . '</textarea>
															<br><br>
															<div align="right"><input type="submit" value="&nbsp;&nbsp;Submit&nbsp;&nbsp;"></div>
														</td>
													</tr>
												</table>
												</form>
											</td>
										</tr>
									</table>
								</td>
							</tr>
						</table>
						</td></tr>
					</table>';
}

sub addNews2 {
	my (@newsitems);
	my ($newsitem);
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
	
	my ($newsDate) = $year.$mon.$mday.$hour.$min.$sec;
	
	$newsSubject =~ s/<[\/]?html>|<head>.*<\/head>|<[\/]?body[^>]*>//mig; #strip out any nasty HTML
	$newsBody =~ s/<[\/]?html>|<head>.*<\/head>|<[\/]?body[^>]*>//mig; #strip out any nasty HTML
	
	my ($CR, $LF) = (chr(13), chr(10));
	
	$newsBody =~ s/[\n|$CR|$LF]{2}/<br \/>/g; # replaces line feed and carriage return characters with <br />'s
	
	push (@newsitems, ($newsDate. ":::" . $newsSubject. ":::" . $newsBody));
	
	if (open (NEWS, "../site_news.txt")) {
		line3: 
		while (<NEWS>) {
			next line3 if $_ =~ /\A#|\A\n/; #skip comments and blank lines
			chomp $_;
			push (@newsitems, $_);
		}
		close (NEWS) || die ("can't close news file: ($!)");
		
		#Rewrite the site news
		replace_file("../site_news.txt", sub {
			local *NEWS=shift;
			foreach my $newsitem (reverse sort @newsitems) {
  				unless (($newsitem =~/\A$newsID/) && ($newsID ne '')) {
  					print NEWS $newsitem . "\n";
  				}
  			}
		}) or die("Could not open the site news","$!");
	}
	
	my($newLogEntry) = "News modified";
	appendLogFile("$logDir/admin.txt", $newLogEntry);
	
	print "Location: $idscgi\n\n";
	exit;
}

sub deleteNews {
	my (@newsitems);
	my ($newsitem);
	
	
	if (open (NEWS, "../site_news.txt")) {
		line3: 
		while (<NEWS>) {
			next line3 if $_ =~ /^#|^\n/; #skip comments and blank lines
			chomp $_;
			push (@newsitems, $_);
		}
		close (NEWS) || die ("can't close news file: ($!)");
	}
	
	replace_file("../site_news.txt", sub {
		local *NEWS = shift;
		foreach my $newsitem (reverse sort @newsitems) {
  			unless ($newsitem =~/\A$newsToDelete/) {
  				print NEWS $newsitem . "\n";
  			}
		    }
	    }) or die("Could not write the site news","$!");
	
	my($newLogEntry) = "News item \"$newsToDelete\" deleted";
	appendLogFile("$logDir/admin.txt", $newLogEntry);
	
	print "Location: $idscgi\n\n";
	exit;
}


sub addAlbum {
	my ($previousalbumtemp);
	
	if ($albumtodisplay =~ /\/.+/) {
		($previousalbumtemp, $albumtitle) = $albumtodisplay =~ /^\/(.+)/;
		$previousalbum = "<a href=\"".$idscgi."?mode=viewalbum&amp;album=".&encodeSpecialChars($previousalbumtemp)."\">&lt; back to album</a>";
	} else {
		($albumtitle) = $albumtodisplay =~ /([^\/]+)$/;
		$previousalbum = "<a href=\"".$idscgi."\">&lt; main page</a>";
	}
	
	$adminContent = $adminContent . '
					<table border="0" cellpadding="0" cellspacing="0" width="400" bgcolor="black" align="center">
						<tr><td>
						<table border="0" cellpadding="0" cellspacing="1" width="400">
							<tr>
								
								<td align="center" valign="middle" bgcolor="gray">
									<table width="300"><tr><td><h2><span class="text">add album</span></h2></td></tr></table>
								</td>
							</tr>
							<tr>
								<td bgcolor="white">
									<table border="0" cellpadding="5" cellspacing="1" width="100%">
										<tr>
											<td>
											<table align="center" cellpadding="5"><tr><td>
												<form action="'.$idscgi.'" method="post">
												<input type="hidden" value="'.$albumtodisplay.'" name="album">
												<input type="hidden" value="addalbum2" name="mode">
												<div class="smallgreytext">You are currently in the directory "albums'.$albumtodisplay.'".<p>
												Create the album: <input type="text" name="newalbumname" size="24" maxlength="200"><br></div>
												<div align="right"><input type="submit" value="&nbsp;&nbsp;Add Album&nbsp;&nbsp;"></div>
												</form>
											</td></tr></table>
											</td>
										</tr>
									</table>
								</td>
							</tr>
						</table>
						</td></tr>
					</table>';
}

sub clearimagecache {
	rmtree($imageCache, 0, 1);
	
	my($newLogEntry) = "Image cache cleared";
	appendLogFile("$logDir/admin.txt", $newLogEntry);
	
	print "Location: $idscgi\n\n";
	exit;
}



sub addAlbum2 {
	$albumtodisplay =~ s/\/\Z//;
	my ($newalbumtemp) = "../albums$albumtodisplay/$newalbumname";
	mkdir($newalbumtemp,0755) || die ("Cannot exec mkdir for \"$newalbumtemp\". $!");
	my ($newalbumdatatemp) = "../album-data$albumtodisplay/$newalbumname";
	mkdir($newalbumdatatemp,0755) || die ("Cannot exec mkdir for \"$newalbumdatatemp\". $!");
	
	my($newLogEntry) = "Album \"$newalbumtemp\" created";
	appendLogFile("$logDir/admin.txt", $newLogEntry);
	
	if ($albumtodisplay =~ /\/.+/) {
		print "Location: $idscgi?mode=viewalbum&album=".&encodeSpecialChars($albumtodisplay)."\n\n";
		exit;
	} else {
		print "Location: $idscgi\n\n";
		exit;
	}
}

sub newAlbumDesc {
	$albumtodisplay =~ s/\/\Z//;
	my ($descfiletemp) = "$albumData/$albumtodisplay/album_description.txt";
	
	$newalbumdesc =~ s/<[\/]*html>|<head>[.*]<\/head>|<[\/]*body[.*]?>//mig; #strip out any nasty HTML
	
	writeItemDesc($descfiletemp, $newalbumdesc);
	
	my($newLogEntry) = "Album \"$albumtodisplay\" description modified";
	appendLogFile("$logDir/admin.txt", $newLogEntry);
	
	if ($albumtodisplay =~ /\/.+/) {
		print "Location: $idscgi?mode=viewalbum&album=".&encodeSpecialChars($albumtodisplay)."\n\n";
		exit;
	} else {
		print "Location: $idscgi\n\n";
		exit;
	}
}

sub uploadFile {
	$albumtodisplay = $uploadDest;
	my ($previousalbumtemp);
	
	if ($albumtodisplay =~ /\/.+/) {
		($previousalbumtemp, $albumtitle) = $albumtodisplay =~ /^\/(.+)/;
		$previousalbum = "<a href=\"".$idscgi."?mode=viewalbum&amp;album=".&encodeSpecialChars($previousalbumtemp)."\">&lt; back to album</a>";
	} else {
		($albumtitle) = $albumtodisplay =~ /([^\/]+)$/;
		$previousalbum = "<a href=\"".$idscgi."\">&lt; main page</a>";
	}
	
	$adminContent = $adminContent . '<table border="0" cellpadding="0" cellspacing="0" width="400" bgcolor="black" align="center">
						<tr><td>
						<table border="0" cellpadding="0" cellspacing="1" width="400">
							<tr>
								
								<td align="center" valign="middle" bgcolor="gray">
									<table width="300"><tr><td><h2><span class="text">upload file</span></h2></td></tr></table>
								</td>
							</tr>
							<tr>
								<td bgcolor="white">
									<table border="0" cellpadding="5" cellspacing="1" width="100%">
										<tr>
											<td>
											<table align="center" cellpadding="5"><tr><td>
												<form action="'.$idscgi.'" method="post" enctype="multipart/form-data">
												<input type="hidden" value="'.$uploadDest.'" name="uploaddest">
												<input type="hidden" value="uploadfile2" name="mode">
												<div class="smallgreytext">You are currently in the directory "albums'.$albumtodisplay.'".<p>
												Upload the file: <input type="file" name="uploadfile" size="16"><p>
												IDS is currently configured to display the following file types: <br>
												<i>'.$fileTypes.'</i><p>
												Additional filetypes can be added in the <a href="./preferences.cgi?mode=albumPrefs" target="_blank">album preferences</a>.</div>
												<div align="right"><input type="submit" value="&nbsp;&nbsp;Upload&nbsp;&nbsp;"></div>
												</form>
											</td></tr></table>
											</td>
										</tr>
									</table>
								</td>
							</tr>
						</table>
						</td></tr>
					</table>';
}

sub uploadFile2 {
	my ($uploadFileRenamed) = $uploadFileName;
	
	if ($uploadFileRenamed =~ /\\/) {
		$uploadFileRenamed =~ /\\([^\\]+)\Z/; # Windows cleanup - strip off full path on user's drive
		$uploadFileRenamed = $1;
	} elsif ($uploadFileRenamed =~ /\//) {
		$uploadFileRenamed =~ /\/([^\/]+)\Z/; # Unix cleanup - strip off full path on user's drive
		$uploadFileRenamed = $1;
	}
	
	$uploadDest = '../albums' . $uploadDest . "/$uploadFileRenamed";
	
	if (-e "$uploadDest") { # does an item with this name already exist?
		die ("Sorry, a file named \"$uploadDest\" already exists.$!");
	}
  	
	replace_file($uploadDest, sub {
		local *FH=shift;
		binmode (FH);
		my $buffer;
		while (my $bytesread=read($uploadFileName,$buffer,1024)) {
			print FH $buffer;
		}
	 }) or bail("couldn't upload file \"$uploadDest\":", $!);

  	
  	my($newLogEntry) = "File \"$uploadDest\" uploaded";
	appendLogFile("$logDir/admin.txt", $newLogEntry);
	
	$albumtodisplay = $uploadDest;
	$albumtodisplay =~ s/\.\.\/albums//;
	$albumtodisplay =~ s/\/$uploadFileRenamed//;
	
	print "Location: $idscgi?mode=viewalbum&album=".&encodeSpecialChars($albumtodisplay)."\n\n";
	exit;
}

sub newImageDesc {
	$imagetoedit =~ s/^\///;
	my($base,$path,$type) = fileparse($imagetoedit, '\.[^.]+\z');
	
	my ($descfiletemp) = "$albumData$path$base"."_desc.txt";
	
	$newimagedesc =~ s/<[\/]*html>|<head[.*]?>.*<\/head>|<[\/]*body[.*]?>//mig; #strip out any nasty HTML
	
	writeItemDesc($descfiletemp, $newimagedesc);
	
	my($newLogEntry) = "image \"$descfiletemp\" description modified";
	appendLogFile("$logDir/admin.txt", $newLogEntry);
	
	print "Location: $idscgi?mode=editimage&image=".&encodeSpecialChars($imagetoedit)."\n\n";
	exit;
}

sub renameImage {
	$itemtorename = "../albums$itemtorename";
	my($base,$path,$type) = fileparse($itemtorename, '\.[^.]+\z');
	if ($extension ne '') {
		$extension = ".$extension";
	}
	my($itemtorenametemp) = $itemtorename;
	$itemtorenametemp =~ s/$base$type\Z/$newname$extension/;
	if ((-e "$itemtorenametemp") && ($itemtorenametemp ne $itemtorename)) { # does an item with this name already exist?
		die ("Sorry, \"$itemtorenametemp\" already exists: $!");
	}
	rename ($itemtorename, $itemtorenametemp) || die ("can't rename \"$itemtorename\" to \"$itemtorenametemp\": ($!)");
	my($newbase,$newpath,$newtype) = fileparse($itemtorenametemp, '\.[^.]+\z');
	my $pathToAlbumData = $path;
	$pathToAlbumData =~ s/..\/albums/$albumData/;
	if (-e "$pathToAlbumData$base"."_desc.txt") { 
		rename ("$pathToAlbumData$base"."_desc.txt", "$pathToAlbumData$newbase"."_desc.txt") || die ("can't rename \"$pathToAlbumData$base"."_desc.txt\" to \"$pathToAlbumData$newbase"."_desc.txt\": ($!)");
	}
	
	$path =~ s/albums/image-cache/;
	unlink (<$path$base\_disp*>);
	
	my($newLogEntry) = "image \"$itemtorename\" renamed to \"$itemtorenametemp\"";
	appendLogFile("$logDir/admin.txt", $newLogEntry);
	
	$imagetoedit = $itemtorenametemp;
	$imagetoedit =~ s/\.\.\/albums//;
	
	print "Location: $idscgi?mode=editimage&image=".&encodeSpecialChars($imagetoedit)."\n\n";
	exit;
}

sub newAlbumIconFromImage {
	$imagetoedit =~ s/^\///;
	my($imagetousetmp) = "../albums/$imagetoedit";
	my($base,$path,$type) = fileparse($imagetousetmp, '\.[^.]+\z');
	my $workingalbum = $path;
	$workingalbum =~ s/\/albums\//\/album-data\//;
	my ($albumfile) = "$workingalbum/album_image.txt";
	
	newAlbumIcon($workingalbum);
		
	generateAlbumPreview($path, $base.$type);
	
	writeItemDesc($albumfile, $imagetoedit);
	
	my($newLogEntry) = "image \"$imagetoedit\" used as album icon";
	appendLogFile("$logDir/admin.txt", $newLogEntry);

	print "Location: $idscgi?mode=editimage&image=".&encodeSpecialChars($imagetoedit)."\n\n";
	exit;
}

sub newAlbumIcon($) {
	my $workingalbum = shift(@_);
	my $workingalbumdir;
	my $withvr="0";
	if (defined $workingalbum) {
		$workingalbumdir="$workingalbum";
		$withvr="1";
	} else {
		$workingalbumdir="$albumData$albumtodisplay";
	}
	
	opendir DATADIR, ("$workingalbumdir") || die ("can't open \"$workingalbumdir\" album-data directory: ($!)");
	my(@AlbumPreviews) = grep /$albumIconName$/, readdir DATADIR;
	closedir DATADIR;
	foreach my $albumPreview (@AlbumPreviews) {
		$albumPreview =~ s/^/\//;
		my $FILE1="$workingalbumdir" . $albumPreview;
		
		unlink $FILE1 || warn "Couldn't unlink \"$albumPreview: $!";
	}
	unlink ("../album-data$albumtodisplay/album_image.txt") || warn "Couldn't remove \"../album-data$albumtodisplay/album_image.txt\": $!";
	return if $withvr;
 	print "Location: $idscgi?mode=viewalbum&album=".&encodeSpecialChars($albumtodisplay)."\n\n";
 	exit;
}

sub rotateImage {
	$itemToRotate = "../albums$itemToRotate";
	my($newLogEntry);
	if ((defined $pathToJpegTran && $pathToJpegTran ne '') && ($itemToRotate =~ /\.jpg\Z||\.jpeg\Z/i)) {
		#perform lossless JPEG rotation
		my($tempImageName) = $itemToRotate.'.new';
		system ("$pathToJpegTran -copy all -rotate $degreesToRotate \"$itemToRotate\" > \"$tempImageName\"") == 0 || die ("Sorry, call to jpegtran failed: $?");
		rename ($tempImageName, $itemToRotate) || die ("Sorry, couldn't rename files to complete lossless rotation: $!");;
		$newLogEntry = "image \"$itemToRotate\" rotated $degreesToRotate degrees. (lossless)";
	} else {
		#perform lossy image rotation
		my($imageToModify) = Image::Magick->new;
		my($x) = $imageToModify->Read($itemToRotate); # read in the picture
		warn "$x" if "$x";
		$imageToModify->Set(quality=>$imageQuality);
		$x = $imageToModify->Rotate(degrees=>$degreesToRotate);
		warn "$x" if "$x";
		$x = $imageToModify->Write($itemToRotate); #write out the picture
		warn "$x" if "$x";
		$newLogEntry = "image \"$itemToRotate\" rotated $degreesToRotate degrees. (lossy)";
	}
	appendLogFile("$logDir/admin.txt", $newLogEntry);
	$imagetoedit = $itemToRotate;
	$imagetoedit =~ s/\.\.\/albums\///;
	print "Location: $idscgi?mode=editimage&image=".&encodeSpecialChars($imagetoedit)."\n\n";
	exit;
}

sub deleteImage {
	$itemtodelete = "../albums$itemtodelete";
	my($base,$path,$type) = fileparse($itemtodelete, '\.[^.]+\z');
	
	my($newpath) = $path;
	my($datapath) = $path;
	$newpath =~ s/..\/albums/$imageCache/;
	$datapath =~ s/..\/albums/$albumData/;
	unlink ($itemtodelete,"$datapath$base"."_desc.txt",
		"$newpath$base"."_disp100.jpg",
		"$newpath$base"."_disp100.info",
		"$newpath$base"."_disp512.jpg",
		"$newpath$base"."_disp512.info",
		"$newpath$base"."_disp640.jpg",
		"$newpath$base"."_disp640.info",
		"$newpath$base"."_disp800.jpg",
		"$newpath$base"."_disp800.info",
		"$newpath$base"."_disp1024.jpg",
		"$newpath$base"."_disp1024.info",
		"$newpath$base"."_disp1600.jpg",
		"$newpath$base"."_disp1600.info");
	my($newLogEntry) = "image \"$itemtodelete\" deleted";
	appendLogFile("$logDir/admin.txt", $newLogEntry);
	
	$albumtodisplay = $path;
	$albumtodisplay =~ s/\.\.\/albums//;
	$albumtodisplay =~ s/\/\Z//;
	
	print "Location: $idscgi?mode=viewalbum&album=".&encodeSpecialChars($albumtodisplay)."&data=".$newpath.$base."\n\n";
	exit;
}

sub renameAlbum2 {
	$itemtorename = "../albums$itemtorename";
  	my($base,$path,$type) = fileparse($itemtorename, '\.[^.]+\z');
	$base='' unless defined $base;
	$type='' unless defined $type;
  	
  	my($itemtorenametemp) = $itemtorename;
  	$itemtorenametemp =~ s/$base$type\Z/$newname$extension/;
	
	my($newbase,$newpath,$newtype) = fileparse($itemtorenametemp, '\.[^.]+\z');
	
	if ((-e "$itemtorenametemp") && ($itemtorenametemp ne $itemtorename)) { # does an item with this name already exist?
		die ("Sorry, \"$itemtorenametemp\" already exists: $!");
  	}
	
	rename ($itemtorename, $itemtorenametemp) ||   die ("can't rename \"$itemtorename\" to \"$itemtorenametemp\": ($!)");
  	
  	my $pathToAlbumData = $itemtorename;
  	$pathToAlbumData =~ s/..\/albums/$albumData/;
  	my $newPathToAlbumData = $itemtorenametemp;
  	$newPathToAlbumData =~ s/..\/albums/$albumData/;
	if (-e "$pathToAlbumData") { 
		rename ("$pathToAlbumData", "$newPathToAlbumData") || die ("can't rename \"$pathToAlbumData\" to \"$newPathToAlbumData\": ($!)");
	}
	
	my $pathToImageCache = $itemtorename;
  	$pathToImageCache =~ s/..\/albums/$imageCache/;
  	my $newPathToImageCache = $itemtorenametemp;
  	$newPathToImageCache =~ s/..\/albums/$imageCache/;
	if (-e "$pathToImageCache") { 
		rename ("$pathToImageCache", "$newPathToImageCache") || die ("can't rename \"$pathToImageCache\" to \"$newPathToImageCache\": ($!)");
	}
	
	my($newLogEntry) = "album \"$itemtorename\" renamed to \"$itemtorenametemp\"";
	appendLogFile("$logDir/admin.txt", $newLogEntry);
	
	$albumtodisplay = $itemtorenametemp;
	$albumtodisplay =~ s/\.\.\/albums//;
	
	print "Location: $idscgi?mode=viewalbum&album=".&encodeSpecialChars($albumtodisplay)."\n\n";
	exit;
}

sub editImage {
	my($base,$path,$type) = fileparse($imagetoedit, '\.[^.]+\z');
	$base = '' unless defined $base;
	my($imageName) = $base . $type;
	
	if ($path =~ /\/.+/) {
		($previousalbumtemp, $albumtitle) = $path =~ /^\/(.+)\//;
		$previousalbum = "<a href=\"".$idscgi."?mode=viewalbum&amp;album=".&encodeSpecialChars($previousalbumtemp)."\">&lt; back to album</a>";
	} else {
		($albumtitle) = $path =~ /([^\/]+)$/;
		$previousalbum = "<a href=\"".$idscgi."\">&lt; main page</a>";
	}
	
	my($origimagepath) = $imagetoedit;
	$imagetoedit = "../albums$imagetoedit";
  	
	createDisplayImage($previewMaxDimension, '', $imagetoedit);
	
	my($xFullSize, $yFullSize) = &getImageDimensions("$imagetoedit");
	my($previewName);
	
	unless (($xFullSize < 512) && ($yFullSize < 512)) {
		createDisplayImage(512, '', $imagetoedit);
		$previewName = &filenameToDisplayName($imagetoedit, 512);
	} else {
		$previewName = $imagetoedit;
	}
  	
  	my($xSize, $ySize) = &getImageDimensions("$previewName");
	$albumContent .= "<span class=\"smallgreytext\"><img src=\"".encodeSpecialChars($previewName)."\" border=\"0\" ";
	$albumContent .= "width=\"$xSize\" " if defined $xSize;
	$albumContent .= "height=\"$ySize\" " if defined $ySize;
	$albumContent .= "alt=\"$imageName\"><br>$imageName</span>\n";
  
  	my($descfilepath) = $albumData . $path . $base;
  	$description = openItemDesc($descfilepath);
  	
	$adminContent .= '<table border="0" cellpadding="0" cellspacing="0" width="500" bgcolor="black" align="center">
						<tr><td>
						<table border="0" cellpadding="0" cellspacing="1" width="500">
							<tr>
								
								<td align="center" valign="middle" bgcolor="gray">
									<table width="400" border="0"><tr><td><h2><span class="text">'. $base .'</span></h2></td></tr></table>
								</td>
							</tr>
							<tr>
								<td>
								<table align="center" cellspacing="5" cellpadding="5" width="600" bgcolor="white" border="0">
									<tr>
										<td bgcolor="#eeeeee">
											<form action="'.$idscgi.'" method="post">
											<input type="hidden" value="'.$origimagepath.'" name="image">
											<input type="hidden" value="newimagedesc" name="mode">
											<span class="smallgreytext">Enter/edit a description of the image "'. $imageName .'" here. Use HTML if you wish.</span><p>
											<textarea name="newimagedesc" cols="60" rows="4" wrap="virtual">'. $description .'</textarea><br>
											<div align="right"><input type="submit" value="&nbsp;&nbsp;OK&nbsp;&nbsp;"></div></form>
										</td>
										<td bgcolor="#eeeeee">
											<form action="'.$idscgi.'" method="post">
											<input type="hidden" value="renameimage" name="mode">
											<input type="hidden" value="'."\L$type".'" name="extension">
											<input type="hidden" value="'.$origimagepath.'" name="itemtorename">
											<span class="smallgreytext">Rename the image here.</span><p>
											<input type="text" name="newname" size="24" maxlength="50" value="'.$base.'">'."\L$type".'<br><br>
											<div align="right"><input type="submit" value="&nbsp;&nbsp;Rename&nbsp;&nbsp;"></div></form>
										</td>
									</tr>
									<tr>
										<td colspan="2"><br>
											<table border="0" cellpadding="2" cellspacing="0" width="650" align="center">
												<tr>
													<td align="center">
														<form action="'.$idscgi.'" method="post">
														<input type="hidden" value="rotateimage" name="mode">
														<input type="hidden" value="270" name="degrees">
														<input type="hidden" value="'.$origimagepath.'" name="itemtorotate">
														<input type="submit" value="&nbsp;&nbsp;&lt; Rotate 90&deg;&nbsp;&nbsp;"></form>
													</td>
													<td align="center">	
														<span class="smallgreytext"> | </span>
													</td>
													<td align="center">	
														<span class="smallgreytext"> <a href="'.$idscgi."?mode=deleteimage&amp;itemtodelete=".&encodeSpecialChars($origimagepath).'">Delete this image</a></span>
													</td>
													<td align="center">	
														<span class="smallgreytext"> | </span>
													</td>
													<td align="center">	
														<span class="smallgreytext"> <a href="'.$idscgi."?mode=newalbumiconfromimage&amp;image=".&encodeSpecialChars($origimagepath).'">Use image for album icon</a></span>
													</td>
													<td align="center">	
														<span class="smallgreytext"> | </span>
													</td>
													<td align="center">	
														<form action="'.$idscgi.'" method="post">
														<input type="hidden" value="rotateimage" name="mode">
														<input type="hidden" value="90" name="degrees">
														<input type="hidden" value="'.$origimagepath.'" name="itemtorotate">
														<input type="submit" value="&nbsp;&nbsp;Rotate 90&deg; &gt;&nbsp;&nbsp;"></form>
													</td>
												</tr>
												<tr>
													<td colspan="7">
														<br><span class="smallgreytext">* Due to browser caching issues, rotated images may not be displayed correctly until they are reloaded.</span>
													</td>
												</tr>
											</table>
										</td>
									</tr>
									<tr>
										<td colspan="3" bgcolor="white">							
											<table align="center" cellpadding="5" width="600" border="0">
												<tr>
													<td align="center">
														'."<img src=\"".&encodeSpecialChars($previewName)."\" border=\"0\" width=\"$xSize\" height=\"$ySize\" alt=\"$imageName\">".'<br>
													</td>
												</tr>
												
											</table>
											<br>
										</td>
									</tr>
								</table>
								</td>
							</tr>
						</table>
						</td></tr>
					</table>';
					
	my($albumtodisplay) = $path;
	$albumtodisplay =~ s/\A\/|\/\Z//g;
	
	opendir ALBUMDIR, ("../albums/$albumtodisplay") || die ("can't open \"../albums/$albumtodisplay\" album directory: ($!)");
	my(@filesInAlbum) = grep !/^\.+/, readdir ALBUMDIR;
	closedir ALBUMDIR;
  	
	my @imagesForPrevNext;
  	THELIST2:
	foreach my $fileInAlbum (sort @filesInAlbum) {
  		next if ($fileInAlbum =~ /_pre\.jpg\Z/i); # this is an old-style preview image- ignore it
  		next if ($fileInAlbum =~ /_disp\d*\.jpg\Z/i); # this is a display image- ignore it

       
		if ($fileInAlbum =~ /\.jpg\Z|\.jpeg\Z|\.gif\Z|\.png\Z|\.mov\Z|\.mpg\Z|\.mpeg\Z|\.mp3\Z/i) { # is this a known format?
			unless ($fileInAlbum =~ /\.mov\Z|\.mpg\Z|\.mpeg\Z|\.mp3\Z/i) {
				push @imagesForPrevNext, $fileInAlbum; # for prev/next thumbs
			}
		}
	}

	my $where;
  	for ($[ .. $#imagesForPrevNext) {
  		$where = $_, last if ($imagesForPrevNext[$_] eq $imageName);
  	}
  
	if ($where > 0)	{ $prevthumb = generatePrevNext($albumtodisplay,$imagesForPrevNext[$where-1],"&lt; previous",'image','../'); }
	if ($where < $#imagesForPrevNext) { $nextthumb = generatePrevNext($albumtodisplay,$imagesForPrevNext[$where+1],"next &gt;",'image','../'); }
  }

sub generateAlbumView{
	my ($previousalbumtemp);

	if ($albumtodisplay =~ /\/.+\//) {
		($previousalbumtemp, $albumtitle) = $albumtodisplay =~ /^(.+)\/([^\/]+)$/;
		$previousalbum = "<a href=\"".$idscgi."?mode=viewalbum&amp;album=".&encodeSpecialChars($previousalbumtemp)."\">&lt; back to album</a>";
	} else {
		($albumtitle) = $albumtodisplay =~ /([^\/]+)$/;
		$previousalbum = "<a href=\"".$idscgi."\">&lt; main page</a>";
	}
	
	#$albumtitle =~ s/\#\d+_//g; # trims off numbers used for list ordering. ex: "#02_"
	#$albumtitle =~ s/_/ /g; # replaces underscores with spaces
	
	my($imagecounter) = 0;
	
	opendir ALBUMDIR, "../albums$albumtodisplay" || die ("can't open \"../albums$albumtodisplay\" album directory: ($!)");
	my(@filesInAlbum) = grep !/^\.+/, readdir ALBUMDIR;
	closedir ALBUMDIR;

	my($fileInAlbum);
  	my(@itemsToDisplay);
	my $imagesInAlbum = 0;
	my $albumsInAlbum = 0;
  	
  	THELIST:
	foreach $fileInAlbum (sort @filesInAlbum) {
      	$fileInAlbum = "../albums$albumtodisplay/" . $fileInAlbum;
		next if ($fileInAlbum =~ /CVS/); # get rid of CVS entries
  		next if ($fileInAlbum =~ /_disp\d*\.jpg\Z/i); # this is a display image- ignore it
		next if ($fileInAlbum =~ /_pre.jpg\Z/i); # this is an old-style preview image- ignore it
			
		if (-d "$fileInAlbum") { # Is this a subdirectory?
	        	push @itemsToDisplay, $fileInAlbum; # if so, remember its name
	        	$albumsInAlbum ++;
        }
        if (displayableItem($fileInAlbum)) { # is this a displayed format?
			push @itemsToDisplay, $fileInAlbum; # if so, remember its name
			$imagesInAlbum ++;
		}
	}
	
	$albumContent = $albumContent.'<table border="0" cellpadding="5" cellspacing="0" width="100%">';
	$albumContent = $albumContent."<tr>\n";
  	
  	
  	# generate album HTML
	foreach my $itemToDisplay (sort @itemsToDisplay) {
  		my($imageName) = $itemToDisplay;
  		$imageName =~ s/\.\.\/albums[\/]*$albumtodisplay\///; #trim off the directory path returned by glob
		
		
		my($filesize) = &fileSize($itemToDisplay);
		my($base,$path,$type) = fileparse($itemToDisplay, '\.[^.]+\z');
		
		my($previewImageSize);
		if ($type =~ /jpg|jpeg|gif|png/i) {	#this is a supported image file
  			createDisplayImage($previewMaxDimension, '', $itemToDisplay);
			my($previewName) = &filenameToDisplayName($itemToDisplay, $previewMaxDimension);
  			my($xSize, $ySize) = &getImageDimensions($previewName);
  			my($prettyImageTitle) = $imageName;
			my($imageToDisplay) = $itemToDisplay;
			$imageToDisplay =~ s/\.\.\/albums[\/]*//; #trim off the directory path returned by glob
			#$prettyImageTitle =~ s/\#\d+_//g;
			$albumContent .= "<td align=\"center\" valign=\"middle\"><a href=\"".$idscgi."?mode=editimage&amp;image=".&encodeSpecialChars($imageToDisplay)."\"><span class=\"smallgreytext\"><img src=\"".&encodeSpecialChars($previewName)."\" border=\"0\" ";
			$albumContent .= "width=\"$xSize\" " if defined $xSize;
			$albumContent.= "height=\"$ySize\" " if defined $ySize;
			$albumContent .= "alt=\"[$prettyImageTitle]\"><br>$prettyImageTitle</span></a></td>\n";
		} elsif (-d $itemToDisplay) { # this is a directory
			my $previewName = $itemToDisplay.'/'.$theme.'.'.$albumIconName;
			$previewName =~ s/\.\.\/albums/..\/album-data/;
			
			unless (-e $previewName) {
				$previewName = generateAlbumPreview($itemToDisplay);
			}
			if ($previewName eq '') {
				$previewName = '../site-images/album_icon.png';
			}
			my($xSize, $ySize) = &getImageDimensions("$previewName");
			# create a link to the directory
			my($dirToDisplay) = $itemToDisplay;
			$dirToDisplay =~ s/\.\.\/albums[\/]*//; #trim off the directory path returned by glob
			#$imageName =~ s/\#\d+_//g; # trims off numbers used for list ordering. ex: "#02_"
  			#$imageName =~ s/_/ /g;
			$albumContent .= "<td align=\"center\" valign=\"middle\"><a href=\"".$idscgi."?mode=viewalbum&amp;album=".encodeSpecialChars($dirToDisplay)."\"><span class=\"smallgreytext\"><img src=\"".encodeSpecialChars($previewName)."\" border=\"0\" ";
			$albumContent .= "width=\"$xSize\" " if defined $xSize;
			$albumContent .="height=\"$ySize\" " if defined $ySize;
			$albumContent .= "alt=\"$imageName\"><br>$imageName</span></a></td>\n";
  		} else { #this is a generic file
  			my $previewName;
			my $extension = $type;
			$extension =~ s/\.//;
			if (-e "../site-images/filetypes/\L$extension".".png") {
				$previewName = "../site-images/filetypes/\L$extension".".png";
			} elsif (-e "../site-images/filetypes/\U$extension".".png") {
				$previewName = "../site-images/filetypes/\U$extension".".png";
			} else {
				$previewName = "../site-images/generic_file.png";
			}
			my($xSize, $ySize) = &getImageDimensions("$previewName");
			my($prettyImageTitle) = $imageName;
			$albumContent = $albumContent."<td align=\"center\" valign=\"middle\"><span class=\"smallgreytext\"><a href=\"../albums/".&encodeSpecialChars("$albumtodisplay/$imageName")."\"><img src=\"".&encodeSpecialChars($previewName)."\" border=\"0\" width=\"$xSize\" height=\"$ySize\" alt=\"$prettyImageTitle\"><br>$prettyImageTitle</a></span></td>\n";
		}
		
		$imagecounter ++;
		if ($imagecounter == $imagesPerRow) { #is it time to go to the next row?
			$albumContent = $albumContent."</tr><tr>\n";
			$imagecounter = 0;
		}
	}
	
	
	if (($imagecounter ne $imagesPerRow)) {
		for (my $i = 0; $i < ($imagesPerRow - $imagecounter); $i++) {
			$albumContent .= "<td>&nbsp;</td>\n"; #put in cells to finish the row (necessary for Netscape)
  		}
  	}
  	
	$albumContent .= "</tr>\n</table>";
  	
	if (($imagesInAlbum == 0) and ($albumsInAlbum == 0)) {$imagesInAlbum = "0";}
  	$totalitems = $imagesInAlbum + $albumsInAlbum;
  	$totalitems = $totalitems.($totalitems == 1 ? ' item' : ' items'); # correct grammar!
	
	return $albumContent;
}

sub openNewsDesc {
	# open news file found at given path
	#
	# each line of an IDS newsfile takes the following format:
	#          news date:::news subject:::news body
	#

	# try to open "local_news.html", "site_news.html", "site_news.txt"
	# first come, first serve

	$sitenews = '<table border="0">';
	my $file = "../site_news.txt";
  	
	if (open (NEWS,$file)) {
		while (<NEWS>) {
			next if $_ =~ /^#|^\n/; #skip comments and blank lines
  			chomp $_;
  			my($newsDate, $newsSubject, $newsBody) = split(/:::/, $_);
			my ($prettyNewsDate) = $newsDate;
			$prettyNewsDate =~ s/\A(\d\d\d\d)(\d\d)(\d\d)(\d\d)(\d\d)\d\d\Z/$2\/$3\/$1<br>$4:$5/;
			$sitenews .= "\n<tr><td valign=\"top\" align=\"center\"><span class=\"misctext\">$prettyNewsDate</span></td><td valign=\"top\"><span class=\"misctext\"><b>$newsSubject</b></span></td></tr><tr><td valign=\"top\" align=\"center\" width=\"100\"><span class=\"smallgreytext\">| <a href=\"".$idscgi."?mode=addnews&amp;newsid=". $newsDate ."\">Modify</a> |<br><br>| <a href=\"".$idscgi."?mode=deletenews&amp;newstodelete=". $newsDate ."\">Delete</a> |</span></td><td><div class=\"misctext\">$newsBody<br></div></td></tr>";
		}
		close (NEWS) || die ("can't close $file: ($!)");
	} else {
		$sitenews = "<tr><td>Sorry, no news file found at \"$file\".</td></tr>";
	}
  	
	$sitenews .= "\n</table>";
}
