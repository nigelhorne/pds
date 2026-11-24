package Web::VWF::Display::albums;

use Web::VWF::Display;

our @ISA = ('Web::VWF::Display');

sub html {
	my $self = shift;
	my %args = (ref($_[0]) eq 'HASH') ? %{$_[0]} : @_;

	# my $info = $self->{_info};
	# my $allowed = {
		# 'page' => 'albums',
		# 'entry' => qr/^A\d+$/,
		# 'lang' => qr/^[A-Z][A-Z]/i,
	# };
	# my %params = %{$info->params({ allow => $allowed })};

	my $albums = $args{'albums'};	# Handle into the database

	# Display list of albums
	return $self->SUPER::html({ updated => $albums->updated(), albums => $albums->selectall_hashref() });
}

1;
