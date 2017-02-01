#!/usr/bin/perl
#
#########################################################################
#
# Image Display System Preview Maker 				6/7/2001     
# 			John Moose			moosejc@muohio.edu
#
#########################################################################
# Use this script to pre-generate your site's preview (thumbnail) images 
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

use File::Basename;
use File::Find;
use File::Path;
use Image::Magick;
use Image::Info qw(image_info);
use strict qw(vars);
use lib qw(./);
use idsShared;

readPreferences('./ids.conf');

$scaledOverlay = Image::Magick->new;
$scaledOverlay->Read("site-images/previewicon.png"); # read in the "scaled" icon to overlay on scaled images

my($logDir) = "./logs";
my($file, $newLogEntry);

print "Locating image files...\n";
find({ wanted => \&findImagesToPreview, follow => 1 }, 'albums/');  #follows symbolic links 

print "Beginning preview generation...\n";

foreach $file (@FilesToPreview) {
	createDisplayImage($previewMaxDimension, '', $file);
	print "Created preview for \"$file\"\n";
}

print "Preview generation complete.\n";
print "Locating albums...\n";
find({ wanted => \&findAlbumsToPreview, follow => 1 }, 'albums/');  #follows symbolic links

my $album;
foreach $album (@AlbumsToPreview) {
	next if ($album eq 'albums');
	foreach my $availableTheme (@availableThemes) {
		$theme = $availableTheme;
		generateAlbumPreview("$album");
		print "Created album icon for \"$album\" - \"$theme\"\n";
	}
}
print "Album icon generation complete.\n";

$newLogEntry = "Preview Maker: Preview generation complete.";
appendLogFile("$logDir/admin.txt", $newLogEntry);


