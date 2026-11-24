#!/usr/bin/env perl

# Can be tested at the command line, e.g.:
#	LANG=en_GB CONFIG_DIR=/home/img.example.com/conf perl -Ilib cgi-bin/page.fcgi page=index
# To mimic a French mobile site:
#	CONFIG_DIR=/home/img.example.com/conf perl -Ilib cgi-bin/page.fcgi --mobile page=index lang=fr
# To turn off the linting of HTML on a search-engine landing page
#	CONFIG_DIR=/home/img.example.com/conf perl -Ilib cgi-bin/page.fcgi --search-engine page=index lint_content=0

BEGIN {
	# Sanitize environment variables
	delete @ENV{qw(IFS CDPATH ENV BASH_ENV)};
	$ENV{'PATH'} = '/usr/local/bin:/bin:/usr/bin';	# For insecurity
	# $ENV{'HOME'} ||= '/home/user';
}

no lib '.';

use strict;
use warnings;
use autodie qw(:all);

use FindBin;

use Web::VWF;

Web::VWF->new({ directory => "$FindBin::Bin/../conf" })->run();
