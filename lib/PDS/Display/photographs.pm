package PDS::Display::photographs;

use strict;
use warnings;

use PDS::Display;
use File::Basename;
use File::Spec;
use Image::Magick::Thumbnail;

our @ISA = ('PDS::Display');

sub http {
	my $self = shift;
	my %args = (ref($_[0]) eq 'HASH') ? %{$_[0]} : @_;

	my $info = $self->{_info};
	my $allowed = {
		'page' => 'photographs',
		'section' => qr/^S\d+$/,	# Takes a section as a parameter
		'entry' => qr/^A\d+$/,	# Takes an album as a parameter
		'lang' => qr/^[A-Z][A-Z]/i,
	};
	my %params = %{$info->params({ allow => $allowed })};

	if(defined($params{'entry'}) && defined($params{'section'})) {
		return $self->SUPER::http();
	}

	# No section chosen, go home
	my $script = $info->script_name();
	return "Location: $script?page=albums";
}

sub html {
	my $self = shift;
	my %args = (ref($_[0]) eq 'HASH') ? %{$_[0]} : @_;

	my $info = $self->{_info};
	my $allowed = {
		'page' => 'photographs',
		'section' => qr/^S\d+$/,	# Takes a section as a parameter
		'entry' => qr/^A\d+$/,	# Takes an album as a parameter
		'lang' => qr/^[A-Z][A-Z]/i,
	};
	my %params = %{$info->params({ allow => $allowed })};

	delete $params{'page'};
	delete $params{'lang'};

	my $photographs = $args{'photographs'};	# Handle into the database
	if(!defined($photographs)) {
		if(my $logger = $self->{_logger}) {
			$logger->warn('photographs not defined');
		}
		return;
	}

	unless(scalar(keys %params)) {
		return $self->SUPER::html(updated => $photographs->updated());
	}

	# Look in the photographs.csv for the name given as the CGI argument and
	# find their details
	# TODO: handle situation where look up fails

	my $albums = $args{'albums'};
	my $sections = $args{'sections'};
	my $pics = $photographs->selectall_hashref(\%params);
	my $rootdir = $self->{_config}->{rootdir} || $self->{_info}->rootdir();

	foreach my $pic(@{$pics}) {
		my $thumbnail = File::Spec->catfile($rootdir, 'thumbs', $pic->{'entry'}, $pic->{'section'}, $pic->{'file'});
		if(!-r $thumbnail) {
			mkdirp(File::Spec->catfile($rootdir, 'thumbs', $pic->{'entry'}, $pic->{'section'}));

			# Create a thumbnail
			my $im = Image::Magick->new();
			my $image = File::Spec->catfile($rootdir, 'img', $pic->{'entry'}, $pic->{'section'}, $pic->{'file'});
			$im->read($image);
			my ($thumb, $x, $y) = Image::Magick::Thumbnail::create($im, 100);
			# use PNG to try to avoid
			#	'Warning: No loadimage plugin for "jpeg:cairo"'
			$thumbnail =~ s/\.jpg$/.png/i;
			$thumb->Write($thumbnail);
			chmod 0444, $thumbnail;
		}
		$pic->{'thumbnail'} = $thumbnail;
	}

	return $self->SUPER::html({
		photographs => $pics,
		album => $albums->fetchrow_hashref(entry => $params{'entry'}),
		section => $sections->fetchrow_hashref(\%params),
		updated => $photographs->updated()
	});
}

# https://www.perlmonks.org/?node_id=366292
sub mkdirp() {
	my $dir = shift;
	return if (-d $dir);
	mkdirp(dirname($dir));
	mkdir($dir);
}

1;
