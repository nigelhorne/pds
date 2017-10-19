package IDS::Display::albums;

use IDS::Display;

our @ISA = ('IDS::Display');

sub html {
	my $self = shift;
	my %args = (ref($_[0]) eq 'HASH') ? %{$_[0]} : @_;

	my $info = $self->{_info};
	my $allowed = {
		'page' => 'albums',
		'entry' => qr/^A\d+$/,
		'lang' => qr/^[A-Z][A-Z]/i,
	};
	my %params = %{$info->params({ allow => $allowed })};

	delete $params{'page'};
	delete $params{'lang'};

	my $albums = $args{'albums'};	# Handle into the database

	unless(scalar(keys %params)) {
		# Display list of albums
		return $self->SUPER::html({ updated => $albums->updated(), albums => $albums->selectall_hashref() });
	}

	# Look in the albums.csv for the name given as the CGI argument and
	# find their details
	# TODO: handle situation where look up fails

	return $self->SUPER::html({
		album => $albums->fetchrow_hashref(\%params),
		decode_base64url => sub {
			MIME::Base64::decode_base64url($_[0])
		},
		updated => $albums->updated()
	});
}

1;
