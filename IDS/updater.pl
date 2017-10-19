#!/usr/bin/perl
#
#########################################################################
#
# Image Display System Updater 				5/23/2001     
# 			Clayton Hynfield			weefle@users.sourceforge.net
#
#########################################################################
# Use this script update from the directory structure of IDS 0.41-0.52 
# installations to that used by IDS 0.711 
#
#########################################################################
#
# Please see the file "README" for more information.
#
#########################################################################
# 
# Copyright (c) 2001, Clayton Hynfield
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

# Change these if you use different names:
my $dirToSearch = './albums/';

#########################################################################


use File::Basename;
use File::Find;
use File::Path;
use Image::Magick;
use strict qw(vars);
use lib qw(./);
use idsShared;

my $debug = 0;
my ($file, $newFile, @albumIcons, @descriptions, @albumDescriptions, @imageDescriptions);

readPreferences('./ids.conf');

print "\n### IDS Updater ###\n\nThis script will upgrade the directory structure of IDS 0.41-0.52\n" 
."installations to that used by IDS 0.72. The directory \"$dirToSearch\" will\n"
."be recursively searched for image descriptions and album descriptions.\n"
."These files will be moved to the \"album-data\" directory and renamed. Old\n"
."album icons will be deleted."
."\n\nEnter \"y\" to continue or any other key to quit: ";

my $choice = <STDIN>;
chomp $choice;
exit unless ($choice eq 'y');



print "\n##########\n\nLocating description and album icon files in \"$dirToSearch\"...\n";
find (\&findFilesToMove, $dirToSearch);

determineDescType();

foreach $file ( @albumIcons ) {
	unless ( unlink $file ) {
		print STDERR "WARNING: Unable to delete album icon \"$file\": $!\n";
	} else {
		print "Deleted album icon \"$file\"\n";
	}
}

foreach $file ( @albumDescriptions ) {
	$newFile = $file;
	$newFile =~ s/\.\/albums\//\.\/album-data\//;
	my ($base, $path, $type) = fileparse($newFile, '\.[^.]+\z');
	unless ( -d $path ) {
		mkpath($path, 0, 0755) || print STDERR "Couldn't create path \"$path\": $!\n";
	}
	$base =~ s/_desc//;
	$newFile = "$path$base/album_description.txt";
	unless ( rename $file, $newFile ) {
		print STDERR "WARNING: Unable to migrate album description \"$file\" to \"$newFile\": $!\n";
	} else {
		print "Migrated album description \"$file\" to \"$newFile\"\n";
	}
}

foreach $file ( @imageDescriptions ) {
	$newFile = $file;
	$newFile =~ s/\.\/albums\//\.\/album-data\//;
	my ($base, $path, $type) = fileparse($newFile, '\.[^.]+\z');
	unless ( -d $path ) {
		mkpath($path, 0, 0755) || print STDERR "Couldn't create path \"$path\": $!\n";
	}
	unless ( rename $file, $newFile ) {
		print STDERR "WARNING: Unable to migrate image description \"$file\" to \"$newFile\": $!\n";
	} else {
		print "Migrated image description \"$file\" to \"$newFile\"\n";
	}
}

sub determineDescType {
	foreach my $descFile ( @descriptions ) {
		my ($base, $path, $type) = fileparse($descFile, '\_desc.txt');
		if (-d "$path$base") {
			push @albumDescriptions, $descFile;
			print "Found album description \"$descFile\"\n" if $debug;
		} else {
			push @imageDescriptions, $descFile;
			print "Found image description \"$descFile\"\n" if $debug;
		}
	}
}

sub findFilesToMove {
	my $file = $_;
	my $fileWithPath = $File::Find::name;
	if ( $file =~ /\A\.album\.jpg\Z/ ) {
		push @albumIcons, $fileWithPath;
		print "Found album icon \"$fileWithPath\"\n" if $debug;
	} elsif ( $file =~ /\.txt\Z/ ) {
		push (@descriptions, $fileWithPath);
		print "Found description \"$fileWithPath\"\n" if $debug;
	}
}

print "Upgrade complete.\n\n";