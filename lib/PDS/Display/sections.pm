package PDS::Display::sections;

use PDS::Display;

our @ISA = ('PDS::Display');

sub html {
	my $self = shift;

	if(my $logger = $self->{_logger}) {
		$logger->trace('Entering ' . __PACKAGE__ . ' html()');
	}

	my %args = (ref($_[0]) eq 'HASH') ? %{$_[0]} : @_;
	my $info = $self->{_info};
	my $allowed = {
		'page' => 'sections',
		'entry' => qr/^A\d+$/,	# Takes an album as a parameters
		'lang' => qr/^[A-Z][A-Z]/i,
	};
	my %params = %{$info->params({ allow => $allowed })};

	delete $params{'page'};
	delete $params{'lang'};

	my $sections = $args{'sections'};	# Handle into the database

	unless(scalar(keys %params)) {
		# No album chosen, list them all
		if(my $logger = $self->{_logger}) {
			$logger->debug('album not defined');
		}
		return $self->SUPER::html({ updated => $sections->updated() });
	}

	# Look in the sections.csv for the name given as the CGI argument and
	# find their details
	# TODO: handle situation where look up fails

	my $albums = $args{'albums'};

	return $self->SUPER::html({
		sections => $sections->selectall_hashref(\%params),
		album => $albums->fetchrow_hashref(\%params),
		updated => $sections->updated()
	});
}

1;
