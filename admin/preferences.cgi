#!/usr/bin/perl
#
#########################################################################
#
# Image Display System Preferences 				6/7/2001     
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
use Carp;
use File::Basename;
use File::Path;
use File::Find;
use Image::Magick;
use Image::Info qw(image_info);
use lib qw(..);
use idsShared;



$imageCache = "../$imageCache";
$albumData = "../$albumData";
$logDir = "../$logDir";

readPreferences('../ids.conf');
readLocalization("../localizations/".$localization.".txt");
  
$query = new CGI;

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
my ($newsDate, $previousalbumtemp, $imageCacheSize);
my ($logSize, $descriptionToWrite, $previewName);
my (@FilesToPreview);

    
# Global variables:

my $results='';  
my ($base,$path,$type) = fileparse($0, '\.[^.]+\z');
my $cgiURL= $base . $type; # get name of this script
  
# Initialize time variables

  
my ($currentDate, $currentTime) = initTime();
  
processData();


if ($mode eq 'home') {
	generateHome();
} elsif ($mode eq 'sitePrefs') {
	sitePrefs();
} elsif ($mode eq 'albumPrefs') {
	albumPrefs();
} elsif ($mode eq 'imagePrefs') {
	imagePrefs();
} elsif ($mode eq 'commentPrefs') {
	commentPrefs();
} elsif ($mode eq 'writePrefs') {
	writePrefs();
} else {
	bail ("Sorry, invalid mode: $!");
}

open (TEMPLATE,"./templates/admin.html") ||
	bail ("Cannot open \"./templates/admin.html\" template for reading: ($!)");
	$pageContent = join '', <TEMPLATE>;
close (TEMPLATE) || bail ("can't close \"./templates/admin.html\" template: ($!)");

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
		unless ($mode =~ /home|sitePrefs|albumPrefs|imagePrefs|commentPrefs|writePrefs/) {$mode = 'home';}
	} else {
		$mode = 'home';
	}
	
	if ($mode eq 'writePrefs') {
		if ($query->param('maxDimension') ne '') {
			$maxDimension = $query->param('maxDimension');
			bail ("Sorry, invalid default image size.$!") unless ($maxDimension =~/\A512\Z|\A640\Z|\A800\Z|\A1024\Z|\A1600\Z|\A9999\Z/);
		}
		if ($query->param('previewMaxDimension') ne '') {
			$previewMaxDimension = $query->param('previewMaxDimension');
			bail ("Sorry, invalid preview max dimension. $!") unless (($previewMaxDimension =~ /\A\d+\Z/) && ($previewMaxDimension >= 1) && ($previewMaxDimension <= 500));
		}
		if ($query->param('imagesPerRow') ne '') {
			$imagesPerRow = $query->param('imagesPerRow');
			bail ("Sorry, invalid number of images per row. $!") unless (($imagesPerRow =~ /\A\d+\Z/) && ($imagesPerRow >= 1) && ($imagesPerRow <= 10));
		}
		if ($query->param('rowsPerPage') ne '') {
			$rowsPerPage = $query->param('rowsPerPage');
			bail ("Sorry, invalid number of rows per page. $!") unless (($rowsPerPage =~ /\A\d+\Z/) && ($rowsPerPage >= 1) && ($rowsPerPage <= 10));
		}
		if ($query->param('scaledImageBorderWidth') ne '') {
			$scaledImageBorderWidth = $query->param('scaledImageBorderWidth');
			bail ("Sorry, invalid scaled image border width. $!") unless (($scaledImageBorderWidth =~ /\A\d+\Z/) && ($scaledImageBorderWidth >= 0) && ($scaledImageBorderWidth <= 10));
		}		
		if ($query->param('displayScaledIcon') ne '') {
			$displayScaledIcon = $query->param('displayScaledIcon');
			bail ("Sorry, invalid choice for 'display scaled icon?'. $!") unless ($displayScaledIcon =~/\Ay\Z|\An\Z/);
		}	
		if ($query->param('imageQuality') ne '') {
			$imageQuality = $query->param('imageQuality');
			bail ("Sorry, invalid image quality. $!") unless (($imageQuality =~ /\A\d+\Z/) && ($imageQuality >= 1) && ($imageQuality <= 100));
		}	
		if ($query->param('guestComments') ne '') {
			$guestComments = $query->param('guestComments');
			bail ("Sorry, invalid choice for 'allow guest comments?'. $!") unless ($guestComments =~/\Ay\Z|\An\Z/);
		}
		if ($query->param('commentAbuserFilter') ne '') {
			$commentAbuserFilter = $query->param('commentAbuserFilter');
			bail ("Sorry, invalid choice for 'comment abuser filter?'. $!") unless ($commentAbuserFilter =~/\Ay\Z|\An\Z/);
		}
		if ($query->param('siteTitle') ne '') {
			$siteTitle = $query->param('siteTitle');
			$siteTitle =~ s/<[\/]?[^>]*>//mig; #strip out any HTML
			$siteTitle =~ s/\t//g; #strip out tabs
		}
		if ($query->param('siteHeader') ne '') {
			$siteHeader = $query->param('siteHeader');
			my ($CR, $LF) = (chr(13), chr(10));
			$siteHeader =~ s/[\n|$CR|$LF]{2}/<br \/>/g; # replaces line feed and carriage return characters with <br />'s
			$siteHeader =~ s/\t//g; #strip out tabs
		}
		if ($query->param('siteFooter') ne '') {
			$siteFooter = $query->param('siteFooter');
			my ($CR, $LF) = (chr(13), chr(10));
			$siteFooter =~ s/[\n|$CR|$LF]{2}/<br \/>/g; # replaces line feed and carriage return characters with <br />'s
			$siteFooter =~ s/\t//g; #strip out tabs
		}
		if ($query->param('albumIconName') ne '') {
			$albumIconName = $query->param('albumIconName');
			bail ("Sorry, invalid choice for 'albumIconName'. $!") unless ($albumIconName =~/^[\w\d\s\-\.]+$/);
		}
		if ($query->param('allowPrints') ne '') {
			$allowPrints = $query->param('allowPrints');
			bail ("Sorry, invalid choice for 'allow prints?'. $!") unless ($allowPrints =~/\Ay\Z|\An\Z/);
		}
		if ($query->param('allowUserTheme') ne '') {
			$allowUserTheme = $query->param('allowUserTheme');
			bail ("Sorry, invalid choice for 'allow theme selection?'. $!") unless ($allowUserTheme =~/\Ay\Z|\An\Z/);
		}
		if ($query->param('displayImageData') ne '') {
			$displayImageData = $query->param('displayImageData');
			bail ("Sorry, invalid choice for 'display image data?'. $!") unless ($displayImageData =~/\Ay\Z|\An\Z/);
		}
		if (defined($query->param('pathToJpegTran'))) {
			$pathToJpegTran = $query->param('pathToJpegTran');
			bail ("Sorry, invalid choice for 'path to jpegtran'. $!") unless ($pathToJpegTran eq '' || -e "$pathToJpegTran");
		}
		if ($query->param('sortMethod') ne '') {
			$sortMethod = $query->param('sortMethod');
			bail ("Sorry, invalid choice for 'sort method'. $!") unless ($sortMethod =~ /name|date|size|intelligent/);
		}
		if ($query->param('maxDisplayedComments') ne '') {
			$maxDisplayedComments = $query->param('maxDisplayedComments');
			bail ("Sorry, invalid number of rows per page. $!") unless (($maxDisplayedComments =~ /\A\d+\Z/) && ($maxDisplayedComments >= 2) && ($maxDisplayedComments <= 50));
		}
		if ($query->param('fileTypes') ne '') {
			$fileTypes = $query->param('fileTypes');
			$fileTypes =~ s/\t/ /g;
			$fileTypes =~ s/\.//g;
		}
		if ($query->param('theme') ne '') {
			$theme = $query->param('theme');
			my $foundTheme = 'n';
			foreach my $availableTheme (@availableThemes) {
				next unless $availableTheme eq $theme;
				$foundTheme = 'y';
			}
			bail ("Sorry, \"$theme\" is an invalid choice for 'theme'. $!") unless ($foundTheme eq 'y');
		}
		if ($query->param('localization') ne '') {
			$localization = $query->param('localization');
			my $foundLang = 'n';
			foreach my $availableLang (@availableLocalizations) {
				next unless $availableLang eq $localization;
				$foundLang = 'y';
			}
			bail ("Sorry, \"$localization\" is an invalid choice for 'localization'. $!") unless ($foundLang eq 'y');
		}
		if ($query->param('embeddedFilter') ne '') {
			$embeddedFilter = $query->param('embeddedFilter');
			my ($CR, $LF) = (chr(13), chr(10));
			$embeddedFilter =~ s/[\n|$CR|$LF]{2}//g; # strip out line feed and carriage return characters
			$embeddedFilter =~ s/\t//g; #strip out tabs
		}
		if ($query->param('collectstats') ne '') {
			$collectstats = $query->param('collectstats');
			bail ("Sorry, invalid choice for 'collect stats?'. $!") unless ($collectstats =~/\Ay\Z|\An\Z/);
		}
	}
	
	$query->delete_all();
}


sub generateHome {
	$adminContent = '<table border="0" cellpadding="0" cellspacing="1" width="400" bgcolor="black" align="center">
						<tr>
							<td>
								<table border="0" cellpadding="0" cellspacing="0" width="400">
									<tr>
										<td colspan="2" align="center" valign="middle" bgcolor="gray">
											<table width="350"><tr><td><h2><span class="text">edit preferences</span></h2></td></tr></table>
										</td>
									</tr>
									<tr>
										<td colspan="2" align="center" valign="middle" bgcolor="white">
											<span class="redtext">'.$results.'</span>
										</td>
									</tr>
									<tr>
										<td align="middle" bgcolor="white" width="200">
											<a href="'.$cgiURL.'?mode=sitePrefs"><br><h3>site</h3><br></a>
										</td>
										<td align="middle" bgcolor="white" width="200">
											<a href="'.$cgiURL.'?mode=albumPrefs"><br><h3>album</h3><br></a>
										</td>
									</tr>
									<tr>
										<td align="middle" bgcolor="white">
											<a href="'.$cgiURL.'?mode=imagePrefs"><h3>image</h3><br></a>
										</td>
										<td align="middle" bgcolor="white"> 
											<a href="'.$cgiURL.'?mode=commentPrefs"><h3>comment</h3><br></a>
										</td>
									</tr>
								</table>
							</td>
						</tr>
					</table>';
	$previousalbum = '<a href="./index.cgi">&lt; back to main page</a>';
}

sub sitePrefs {
	$previousalbum = "<a href=\"".$cgiURL."\">&lt; back to main preferences</a>";
	$adminContent .= '
					<table border="0" cellpadding="0" cellspacing="0" width="400" bgcolor="black" align="center">
						<tr><td>
						<table border="0" cellpadding="0" cellspacing="1" width="400">
							<tr>
								
								<td align="center" valign="middle" bgcolor="gray">
									<table width="350"><tr><td><h2><span class="text">edit site preferences</span></h2></td></tr></table>
								</td>
							</tr>
							<tr>
								<td bgcolor="white">
									<table border="0" cellpadding="5" cellspacing="1" width="300">
										<tr>
											<td>
											<table align="center" cellpadding="5"><tr><td>
												<form action="'.$cgiURL.'" method="post">
												<input type="hidden" value="writePrefs" name="mode">												
												<table border="0" cellpadding="5" cellspacing="1" align="center" width="350">
													<tr>
														<td><b><span class="smallgreytext">Site name</span></b></td><td><input type="text" name="siteTitle" size="20" maxlength="40" value="'.$siteTitle.'"></td>
													</tr>
													<tr>
														<td colspan="2">
															<table align="right" border="0" cellspacing="0" cellpadding="5" width="300">
																<tr>
																	<td>
																		<div class="smallgreytext">The name of this site. Used in page titles.</div>
																	</td>
																</tr>
															</table>
														</td>
													</tr>
													
													<tr>
														<td><b><span class="smallgreytext">Site Header</span></b></td><td></td>
													</tr>
													<tr>
														<td colspan="2" align="right"><textarea name="siteHeader" cols="50" rows="4" wrap="virtual">'.$siteHeader.'</textarea></td>
													</tr>
													<tr>
														<td colspan="2">
															<table align="right" border="0" cellspacing="0" cellpadding="5" width="300">
																<tr>
																	<td>
																		<div class="smallgreytext">Header printed at the top of the home, image, and search pages. HTML is allowed.</div>
																	</td>
																</tr>
															</table>
														</td>
													</tr>
													<tr>
														<td><b><span class="smallgreytext">Site Footer</span></b></td><td></td>
													</tr>
													<tr>
														<td colspan="2" align="right"><textarea name="siteFooter" cols="50" rows="4" wrap="virtual">'.$siteFooter.'</textarea></td>
													</tr>
													<tr>
														<td colspan="2">
															<table align="right" border="0" cellspacing="0" cellpadding="5" width="300">
																<tr>
																	<td>
																		<div class="smallgreytext">Footer printed at the bottom of every page. HTML is allowed.</div>
																	</td>
																</tr>
															</table>
														</td>
													</tr>
													<tr>
														<td><b><span class="smallgreytext">Perform Stats Collection?</span></b>
														</td>
														<td>
															<select name="collectstats" size="1">
																<option value="y"'.($collectstats eq 'y' ? ' selected' : '').'>Yes
																<option value="n"'.($collectstats eq 'n' ? ' selected' : '').'>No
															</select>
														</td>
													</tr>
													<tr>
														<td colspan="2">
															<table align="right" border="0" cellspacing="0" cellpadding="5" width="300">
																<tr>
																	<td>
																		<div class="smallgreytext">Store access count in "'.$albumData.'/statsfile". (No)</div>
																	</td>
																</tr>
															</table>
															
														</td>
													</tr>
													
													<tr>
														<td><b><span class="smallgreytext">Localization</span></b>
														</td>
														<td>
															<select name="localization" size="1">';
	foreach my $availableLang (@availableLocalizations) {
		$adminContent .= '<option value="'.$availableLang.'"'.($availableLang eq $localization ? ' selected' : '').'>'.$availableLang;
	}
	$adminContent .= '</select>
														</td>
													</tr>
													<tr>
														<td colspan="2">
															<table align="right" border="0" cellspacing="0" cellpadding="5" width="300">
																<tr>
																	<td>
																		<div class="smallgreytext">Default language to be used by IDS. (English)</div>
																	</td>
																</tr>
															</table>
															
														</td>
													</tr>
													
													<tr>
														<td><b><span class="smallgreytext">Allow Theme Selection?</span></b>
														</td>
														<td>
															<select name="allowUserTheme" size="1">
																<option value="y"'.($allowUserTheme eq 'y' ? ' selected' : '').'>Yes
																<option value="n"'.($allowUserTheme eq 'n' ? ' selected' : '').'>No
															</select>
														</td>
													</tr>
													<tr>
														<td colspan="2">
															<table align="right" border="0" cellspacing="0" cellpadding="5" width="300">
																<tr>
																	<td>
																		<div class="smallgreytext">Allow guests to select what theme they use to view the albums</a>. (Yes)</div>
																	</td>
																</tr>
															</table>
														</td>
													</tr>
													<tr>
														<td><b><span class="smallgreytext">Theme</span></b>
														</td>
														<td>
															<select name="theme" size="1">';
	foreach my $availableTheme (@availableThemes) {
		$adminContent .= '<option value="'.$availableTheme.'"'.($availableTheme eq $theme ? ' selected' : '').'>'.$availableTheme;
	}
	$adminContent .= '</select>
														</td>
													</tr>
													<tr>
														<td colspan="2">
															<table align="right" border="0" cellspacing="0" cellpadding="5" width="300">
																<tr>
																	<td>
																		<div class="smallgreytext">Graphical theme to apply to all pages by default. (Ziggo)</div>
																	</td>
																</tr>
															</table>
															
														</td>
													</tr>
												</table>
												<br>
												<br>
												<br>
												<div align="right"><input type="submit" value="&nbsp;&nbsp;Save&nbsp;&nbsp;"></div>
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

sub albumPrefs {
	$previousalbum = "<a href=\"".$cgiURL."\">&lt; back to main preferences</a>";
	$adminContent .= '
					<table border="0" cellpadding="0" cellspacing="0" width="400" bgcolor="black" align="center">
						<tr><td>
						<table border="0" cellpadding="0" cellspacing="1" width="400">
							<tr>
								
								<td align="center" valign="middle" bgcolor="gray">
									<table width="350"><tr><td><h2><span class="text">edit album preferences</span></h2></td></tr></table>
								</td>
							</tr>
							<tr>
								<td bgcolor="white">
									<table border="0" cellpadding="5" cellspacing="1" width="300">
										<tr>
											<td>
											<table align="center" cellpadding="5"><tr><td>
												<form action="'.$cgiURL.'" method="post">
												<input type="hidden" value="writePrefs" name="mode">												
												<table border="0" cellpadding="5" cellspacing="1" align="center" width="350">
													
													<tr>
														<td><b><span class="smallgreytext">Preview/thumbnail max dimension</span></b></td><td><input type="text" name="previewMaxDimension" size="6" maxlength="3" value="'.$previewMaxDimension.'"></td>
													</tr>
													<tr>
														<td colspan="2">
															<table align="right" border="0" cellspacing="0" cellpadding="5" width="300">
																<tr>
																	<td>
																		<div class="smallgreytext">Size (in pixels) of the longest side of a thumbnail/preview image. <span class="redtext">*</span> (100)</div>
																	</td>
																</tr>
															</table>
															
														</td>
													</tr>
													<tr>
														<td><b><span class="smallgreytext">Images per row</span></b></td><td><input type="text" name="imagesPerRow" size="6" maxlength="3" value="'.$imagesPerRow.'"></td>
													</tr>
													<tr>
														<td colspan="2">
															<table align="right" border="0" cellspacing="0" cellpadding="5" width="300">
																<tr>
																	<td>
																		<div class="smallgreytext">Number of images displayed on each row in an album. Must be between 1 and 10. (3)</div>
																	</td>
																</tr>
															</table>
															
														</td>
													</tr>
													<tr>
														<td><b><span class="smallgreytext">Rows per page</span></b></td><td><input type="text" name="rowsPerPage" size="6" maxlength="3" value="'.$rowsPerPage.'"></td>
													</tr>
													<tr>
														<td colspan="2">
															<table align="right" border="0" cellspacing="0" cellpadding="5" width="300">
																<tr>
																	<td>
																		<div class="smallgreytext">Number of rows displayed on each page in an album. Must be between 1 and 10. (4)</div>
																	</td>
																</tr>
															</table>
															
														</td>
													</tr>
													<tr>
														<td><b><span class="smallgreytext">Scaled image border width</span></b></td><td><input type="text" name="scaledImageBorderWidth" size="6" maxlength="3" value="'.$scaledImageBorderWidth.'"></td>
													</tr>
													<tr>
														<td colspan="2">
															<table align="right" border="0" cellspacing="0" cellpadding="5" width="300">
																<tr>
																	<td>
																		<div class="smallgreytext">Width (in pixels) of the border around thumbnails/scaled images (0 for no border). <span class="redtext">*</span> (1)</div>
																	</td>
																</tr>
															</table>
															
														</td>
													</tr>
													<tr>
														<td><b><span class="smallgreytext">Display "thumbnail" corner icon?</span></b>
														</td>
														<td>
															<select name="displayScaledIcon" size="1">
																<option value="y"'.($displayScaledIcon eq 'y' ? ' selected' : '').'>Yes
																<option value="n"'.($displayScaledIcon eq 'n' ? ' selected' : '').'>No
															</select>
														</td>
													</tr>
													<tr>
														<td colspan="2">
															<table align="right" border="0" cellspacing="0" cellpadding="5" width="300">
																<tr>
																	<td>
																		<div class="smallgreytext">Display an icon (<i>IDS-Root</i>/site-images/previewicon.png) in the bottom-right corner of thumbnail images. <span class="redtext">*</span> (Yes)</div>
																	</td>
																</tr>
															</table>
															
														</td>
													</tr>
													
													<tr>
														<td><b><span class="smallgreytext">Default sort method</span></b>
														</td>
														<td>
															<select name="sortMethod" size="1">
																<option value="name"'.($sort eq 'name' ? ' selected' : '').'>Sort by name
																<option value="date"'.($sort eq 'date' ? ' selected' : '').'>Sort by date
																<option value="size"'.($sort eq 'size' ? ' selected' : '').'>Sort by filesize
																<option value="intelligent"'.($sort eq 'intelligent' ? ' selected' : '').'>Intelligent name sort
															</select>
														</td>
													</tr>
													<tr>
														<td colspan="2">
															<table align="right" border="0" cellspacing="0" cellpadding="5" width="300">
																<tr>
																	<td>
																		<div class="smallgreytext">The default method by which to sort images in albums. This choice can be overridden by users. (Sort by name)</div>
																	</td>
																</tr>
															</table>
															
														</td>
													</tr>
													
													<tr>
														<td><b><span class="smallgreytext">Other file types to display</span></b></td><td><input type="text" name="fileTypes" size="30" maxlength="120" value="'.$fileTypes.'"></td>
													</tr>
													<tr>
														<td colspan="2">
															<table align="right" border="0" cellspacing="0" cellpadding="5" width="300">
																<tr>
																	<td>
																		<div class="smallgreytext">File types (extensions) you would like IDS to display, separated by spaces. (jpg jpeg gif png mov mpg mpeg mp3)</div>
																	</td>
																</tr>
															</table>
															
														</td>
													</tr>
												</table>
												<br>
												<br>
												<div class="smallgreytext" align="left"><i><span class="redtext">*</span> You must delete the image-cache for this option to take effect.</i></div>

												<br>
												<div align="right"><input type="submit" value="&nbsp;&nbsp;Save&nbsp;&nbsp;"></div>
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

sub imagePrefs {
	$previousalbum = "<a href=\"".$cgiURL."\">&lt; back to main preferences</a>";
	$adminContent .= '
					<table border="0" cellpadding="0" cellspacing="0" width="400" bgcolor="black" align="center">
						<tr><td>
						<table border="0" cellpadding="0" cellspacing="1" width="400">
							<tr>
								
								<td align="center" valign="middle" bgcolor="gray">
									<table width="350"><tr><td><h2><span class="text">edit image preferences</span></h2></td></tr></table>
								</td>
							</tr>
							<tr>
								<td bgcolor="white">
									<table border="0" cellpadding="5" cellspacing="1" width="300">
										<tr>
											<td>
											<table align="center" cellpadding="5"><tr><td>
												<form action="'.$cgiURL.'" method="post">
												<input type="hidden" value="writePrefs" name="mode">												
												<table border="0" cellpadding="5" cellspacing="1" align="center" width="350">
													<tr>
														<td><b><span class="smallgreytext">Default image size</span></b>
														</td>
														<td>
															<select name="maxDimension" size="1">
																<option value="512"'.($maxDimension == 512 ? ' selected' : '').'>tiny (512)
																<option value="640"'.($maxDimension == 640 ? ' selected' : '').'>small (640)
																<option value="800"'.($maxDimension == 800 ? ' selected' : '').'>medium (800)
																<option value="1024"'.($maxDimension == 1024 ? ' selected' : '').'>large (1024)
																<option value="1600"'.($maxDimension == 1600 ? ' selected' : '').'>x-large (1600)
																<option value="9999"'.($maxDimension == 9999 ? ' selected' : '').'>original
															</select>	
														</td>
													</tr>
													<tr>
														<td colspan="2">
															<table align="right" border="0" cellspacing="0" cellpadding="5" width="300">
																<tr>
																	<td>
																		<div class="smallgreytext">Default size (in pixels) of the longest side the images displayed by IDS. (512)</div>
																	</td>
																</tr>
															</table>
															
														</td>
													</tr>
													<tr>
														<td><b><span class="smallgreytext">Scaled image border width</span></b></td><td><input type="text" name="scaledImageBorderWidth" size="6" maxlength="3" value="'.$scaledImageBorderWidth.'"></td>
													</tr>
													<tr>
														<td colspan="2">
															<table align="right" border="0" cellspacing="0" cellpadding="5" width="300">
																<tr>
																	<td>
																		<div class="smallgreytext">Width (in pixels) of the border around thumbnails/scaled images (0 for no border). <span class="redtext">*</span> (2)</div>
																	</td>
																</tr>
															</table>
															
														</td>
													</tr>
													<tr>
														<td><b><span class="smallgreytext">Resized image quality</span></b></td><td><input type="text" name="imageQuality" size="6" maxlength="3" value="'.$imageQuality.'"></td>
													</tr>
													<tr>
														<td colspan="2">
															<table align="right" border="0" cellspacing="0" cellpadding="5" width="300">
																<tr>
																	<td>
																		<div class="smallgreytext">The quality at which resized images and thumbnails are saved. A percentage from 1 (worst) to 100 (best). <span class="redtext">*</span> (85)</div>
																	</td>
																</tr>
															</table>
														</td>
													</tr>
													
													<tr>
														<td><b><span class="smallgreytext">Display image data?</span></b>
														</td>
														<td>
															<select name="displayImageData" size="1">
																<option value="y"'.($displayImageData eq 'y' ? ' selected' : '').'>Yes
																<option value="n"'.($displayImageData eq 'n' ? ' selected' : '').'>No
															</select>
														</td>
													</tr>
													<tr>
														<td colspan="2">
															<table align="right" border="0" cellspacing="0" cellpadding="5" width="300">
																<tr>
																	<td>
																		<div class="smallgreytext">Display the EXIF tags or JPEG comments embedded in some image files. (Yes)</div>
																	</td>
																</tr>
															</table>
														</td>
													</tr>
													
													<tr>
														<td><b><span class="smallgreytext">Allow print ordering?</span></b>
														</td>
														<td>
															<select name="allowPrints" size="1">
																<option value="y"'.($allowPrints eq 'y' ? ' selected' : '').'>Yes
																<option value="n"'.($allowPrints eq 'n' ? ' selected' : '').'>No
															</select>
														</td>
													</tr>
													<tr>
														<td colspan="2">
															<table align="right" border="0" cellspacing="0" cellpadding="5" width="300">
																<tr>
																	<td>
																		<div class="smallgreytext">Allow guests to order prints from <a href="http://www.shutterfly.com/">ShutterFly.com</a>. (Yes)</div>
																	</td>
																</tr>
															</table>
														</td>
													</tr>
													
  													<tr>
														<td><b><span class="smallgreytext">Path to jpegtran</span></b></td><td><input type="text" name="pathToJpegTran" size="20" maxlength="50" value="'.$pathToJpegTran.'"></td>
													</tr>
													<tr>
														<td colspan="2">
															<table align="right" border="0" cellspacing="0" cellpadding="5" width="300">
																<tr>
																	<td>
																		<div class="smallgreytext">Path to the jpegtran utility. If this utility is installed, JPEG image rotations can be performed losslessly.</div>
  																	</td>
  																</tr>
  															</table>
  														</td>
  													</tr>
  													<tr>
	 													<td colspan="2"><b><span class="smallgreytext">Embedded comment filter</span></b></td>
	 												</tr>
  													<tr>	
	 													<td colspan="2"><textarea name="embeddedFilter" cols="50" rows="4" wrap="virtual">'.$embeddedFilter.'</textarea></td>
	 												</tr>
	 												<tr>
	 													<td colspan="2">
	 														<table align="right" border="0" cellspacing="0" cellpadding="5" width="300">
	 															<tr>
	 																<td>
	 																	<div class="smallgreytext">Regular expression by which to filter embedded comments, eg. signatures left by XV and Photoshop.</div>
	   																</td>
	   															</tr>
	   														</table>
   														</td>
	   												</tr>
												</table>
												<br>
												<br>
												<div class="smallgreytext" align="left"><i><span class="redtext">*</span> You must delete the image-cache for this option to take effect.</i></div>

												<br>
												<div align="right"><input type="submit" value="&nbsp;&nbsp;Save&nbsp;&nbsp;"></div>
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

sub commentPrefs {
	$previousalbum = "<a href=\"".$cgiURL."\">&lt; back to main preferences</a>";
	$adminContent .= '
					<table border="0" cellpadding="0" cellspacing="0" width="400" bgcolor="black" align="center">
						<tr><td>
						<table border="0" cellpadding="0" cellspacing="1" width="400">
							<tr>
								
								<td align="center" valign="middle" bgcolor="gray">
									<table width="350"><tr><td><h2><span class="text">edit comment preferences</span></h2></td></tr></table>
								</td>
							</tr>
							<tr>
								<td bgcolor="white">
									<table border="0" cellpadding="5" cellspacing="1" width="300">
										<tr>
											<td>
											<table align="center" cellpadding="5"><tr><td>
												<form action="'.$cgiURL.'" method="post">
												<input type="hidden" value="writePrefs" name="mode">												
												<table border="0" cellpadding="5" cellspacing="1" align="center" width="350">
													
													<tr>
														<td><b><span class="smallgreytext">Allow guest comments?</span></b>
														</td>
														<td>
															<select name="guestComments" size="1">
																<option value="y"'.($guestComments eq 'y' ? ' selected' : '').'>Yes
																<option value="n"'.($guestComments eq 'n' ? ' selected' : '').'>No
															</select>
														</td>
													</tr>
													<tr>
														<td colspan="2">
															<table align="right" border="0" cellspacing="0" cellpadding="5" width="300">
																<tr>
																	<td>
																		<div class="smallgreytext">Allow guests to post comments about images. (Yes)</div>
																	</td>
																</tr>
															</table>
														</td>
													</tr>
													<tr>
														<td><b><span class="smallgreytext">Comment abuser filtering?</span></b>
														</td>
														<td>
															<select name="commentAbuserFilter" size="1">
																<option value="y"'.($commentAbuserFilter eq 'y' ? ' selected' : '').'>Yes
																<option value="n"'.($commentAbuserFilter eq 'n' ? ' selected' : '').'>No
															</select>
														</td>
													</tr>
													<tr>
														<td colspan="2">
															<table align="right" border="0" cellspacing="0" cellpadding="5" width="300">
																<tr>
																	<td>
																		<div class="smallgreytext">Ban comment posters who use words listed in "postcomment/words.txt". (No)</div>
																	</td>
																</tr>
															</table>
														</td>
													</tr>
													<tr>
														<td><b><span class="smallgreytext">Max Comments Displayed</span></b></td><td><input type="text" name="maxDisplayedComments" size="6" maxlength="3" value="'.$maxDisplayedComments.'"></td>
													</tr>
													<tr>
														<td colspan="2">
															<table align="right" border="0" cellspacing="0" cellpadding="5" width="300">
																<tr>
																	<td>
																		<div class="smallgreytext">Maximum number of comments displayed by the comment viewer CGI. Must be between 2 and 50. (10)</div>
																	</td>
																</tr>
															</table>
															
														</td>
													</tr>
												</table>
												<br>
												<br>
												<div class="smallgreytext" align="left"><i><span class="redtext">*</span> You must delete the image-cache for this option to take effect.</i></div>

												<br>
												<div align="right"><input type="submit" value="&nbsp;&nbsp;Save&nbsp;&nbsp;"></div>
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


sub writePrefs {
	replace_file('../ids.conf',sub {
	local *FH = shift;
  	print FH "# Please do not edit this file manually. Use the IDS Admin CGI to make changes.\n\n";
  	print FH "maxDimension\t$maxDimension\n";
	print FH "previewMaxDimension\t$previewMaxDimension\n";
	print FH "imagesPerRow\t$imagesPerRow\n";
	print FH "rowsPerPage\t$rowsPerPage\n";
	print FH "scaledImageBorderWidth\t$scaledImageBorderWidth\n";
	print FH "displayScaledIcon\t$displayScaledIcon\n";
	print FH "imageQuality\t$imageQuality\n";
	print FH "guestComments\t$guestComments\n";
	print FH "commentAbuserFilter\t$commentAbuserFilter\n";
	print FH "siteTitle\t$siteTitle\n";
	print FH "siteHeader\t$siteHeader\n";
  	print FH "siteFooter\t$siteFooter\n";
  	print FH "displayImageData\t$displayImageData\n";
  	print FH "allowPrints\t$allowPrints\n";
  	print FH "albumIconName\t$albumIconName\n";
  	print FH "pathToJpegTran\t$pathToJpegTran\n";
  	print FH "sortMethod\t$sortMethod\n";
  	print FH "maxDisplayedComments\t$maxDisplayedComments\n";
  	print FH "localization\t$localization\n";
  	print FH "theme\t$theme\n";
  	print FH "embeddedFilter\t$embeddedFilter\n";
  	print FH "allowUserTheme\t$allowUserTheme\n";
  	print FH "fileTypes\t$fileTypes\n";
  	print FH "collectstats\t$collectstats\n";
  	});
	
	my($newLogEntry) = "Preferences modified";
	appendLogFile("$logDir/admin.txt", $newLogEntry);
	
	$results = "Your changes have been saved.";
	generateHome();
}
