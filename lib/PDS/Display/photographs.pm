package PDS::Display::photographs;

use PDS::Display;

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

	return $self->SUPER::html({
		photographs => $photographs->selectall_hashref(\%params),
		album => $albums->fetchrow_hashref(entry => $params{'entry'}),
		section => $sections->fetchrow_hashref(\%params),
		updated => $photographs->updated()
	});
}

1;
