package PDS::DB::sections;

# The database associated with the sections

use Database::Abstraction;

our @ISA = ('Database::Abstraction');

# The entry column is not unique, so don't slurp it
sub new
{
	my $class = shift;
	my %args = (ref($_[0]) eq 'HASH') ? %{$_[0]} : @_;

	return $class->SUPER::new(max_slurp_size => 0, %args);
}

1;
