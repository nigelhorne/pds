#!/usr/bin/env perl

# PDS is licensed under GPL2.0 for personal use only
# njh@bandsman.co.uk

# Based on VWF - https://github.com/nigelhorne/vwf

# Can be tested at the command line, e.g.:
#	LANG=en_GB root_dir=$(pwd)/.. ./page.fcgi page=index
# To mimic a French mobile site:
#	root_dir=$(pwd)/.. ./page.fcgi mobile=1 page=index lang=fr
# To turn off linting of HTML on a search-engine landing page
#	LANG=en_GB root_dir=$(pwd)/.. ./page.fcgi --search-engine page=index lint_content=0

use strict;
use warnings;
# use diagnostics;

BEGIN {
	# Sanitize environment variables
	delete @ENV{qw(IFS CDPATH ENV BASH_ENV)};
	$ENV{'PATH'} = '/usr/local/bin:/bin:/usr/bin';	# For insecurity
}

no lib '.';

use Log::Log4perl qw(:levels);	# Put first to cleanup last
use CGI::Carp qw(fatalsToBrowser);
use CGI::Info;
use CGI::Lingua 0.61;
use Class::Simple;
use File::Basename;
# use CGI::Alert $ENV{'SERVER_ADMIN'} || 'you@example.com';
use FCGI;
use FCGI::Buffer;
use File::HomeDir;
use Log::Any::Adapter;
use Error qw(:try);
use File::Spec;
use Log::WarnDie 0.09;
use CGI::ACL;
use HTTP::Date;
use POSIX qw(strftime);
use Readonly;
use Time::HiRes;

# FIXME: Sometimes gives Insecure dependency in require while running with -T switch in Module/Runtime.pm
# use Taint::Runtime qw($TAINT taint_env);
use autodie qw(:all);

# use lib '/usr/lib';	# This needs to point to the PDS directory lives,
			# i.e. the contents of the lib directory in the
			# distribution
use lib '../lib';

use PDS::Config;

# $TAINT = 1;
# taint_env();

Log::WarnDie->filter(\&filter);

my $info = CGI::Info->new();
my $tmpdir = $info->tmpdir();
my $script_dir = $info->script_dir();
my $config;

my @suffixlist = ('.pl', '.fcgi');
my $script_name = basename($info->script_name(), @suffixlist);

if($ENV{'HTTP_USER_AGENT'}) {
	# open STDERR, ">&STDOUT";
	close STDERR;
	open(STDERR, '>>', "$tmpdir/$script_name.stderr");
}

my $vwflog;	# Location of the vwf.log file, read in from the config file - default = logdir/vwf.log

my $infocache;
my $linguacache;
my $buffercache;

Log::Log4perl->init("$script_dir/../conf/$script_name.l4pconf");
my $logger = Log::Log4perl->get_logger($script_name);
Log::WarnDie->dispatcher($logger);

# my $pagename = "PDS::Display::$script_name";
# eval "require $pagename";
use PDS::Display::albums;
use PDS::Display::sections;
use PDS::Display::photographs;
use PDS::Display::upload;
use PDS::Display::meta_data;

use PDS::DB::albums;
if($@) {
	$logger->error($@);
	die $@;
}
use PDS::DB::sections;
use PDS::DB::photographs;

my $database_dir = "$script_dir/../databases";
Database::Abstraction::init({
	cache => CHI->new(driver => 'Memory', datastore => {}),
	cache_duration => '1 day',
	directory => $database_dir,
	logger => $logger
});

my $albums = PDS::DB::albums->new();
if($@) {
	$logger->error($@);
	Log::WarnDie->dispatcher(undef);
	die $@;
}
my $sections = PDS::DB::sections->new();
my $photographs = PDS::DB::photographs->new();

# http://www.fastcgi.com/docs/faq.html#PerlSignals
my $requestcount = 0;
my $handling_request = 0;
my $exit_requested = 0;
my %blacklisted_ip;

# CHI->stats->enable();

my $rate_limit_cache;	# Rate limit clients by IP address
Readonly my @rate_limit_trusted_ips => ('127.0.0.1', '192.168.1.1');

Readonly my @blacklist_country_list => (
	'BY', 'MD', 'RU', 'CN', 'BR', 'UY', 'TR', 'MA', 'VE', 'SA', 'CY',
	'CO', 'MX', 'IN', 'RS', 'PK', 'UA', 'XH'
);

my $acl = CGI::ACL->new()->deny_country(country => \@blacklist_country_list)->allow_ip('108.44.193.70')->allow_ip('127.0.0.1');

sub sig_handler {
	$exit_requested = 1;
	$logger->trace('In sig_handler');
	if(!$handling_request) {
		$logger->info('Shutting down');
		if($buffercache) {
			$buffercache->purge();
		}
		CHI->stats->flush();
		Log::WarnDie->dispatcher(undef);
		exit(0);
	}
}

$SIG{USR1} = \&sig_handler;
$SIG{TERM} = \&sig_handler;
$SIG{PIPE} = 'IGNORE';
$ENV{'PATH'} = '/usr/local/bin:/bin:/usr/bin';	# For insecurity

$Error::Debug = 1;

$SIG{__WARN__} = sub { die @_ };

my $request = FCGI::Request();

# It would be really good to send 429 to search engines when there are more than, say, 5 requests being handled.
# But I don't think that's possible with the FCGI module

while($handling_request = ($request->Accept() >= 0)) {
	unless($ENV{'REMOTE_ADDR'}) {
		# debugging from the command line
		$ENV{'NO_CACHE'} = 1;
		if((!defined($ENV{'HTTP_ACCEPT_LANGUAGE'})) && defined($ENV{'LANG'})) {
			my $lang = $ENV{'LANG'};
			$lang =~ s/\..*$//;
			$lang =~ tr/_/-/;
			$ENV{'HTTP_ACCEPT_LANGUAGE'} = lc($lang);
		}
		Log::Any::Adapter->set('Stdout', log_level => 'trace');
		$logger = Log::Any->get_logger(category => $script_name);
		Log::WarnDie->dispatcher($logger);
		$albums->set_logger($logger);
		$info->set_logger($logger);
		# CHI->stats->enable();
		try {
			doit(debug => 1);
		} catch Error with {
			my $msg = shift;
			warn "$msg\n", $msg->stacktrace();
			$logger->error($msg);
		};
		last;
	}

	$requestcount++;
	Log::Any::Adapter->set( { category => $script_name }, 'Log4perl');
	$logger = Log::Any->get_logger(category => $script_name);
	$logger->info("Request $requestcount: ", $ENV{'REMOTE_ADDR'});
	$albums->set_logger($logger);
	$info->set_logger($logger);

	my $start = [Time::HiRes::gettimeofday()];

	try {
		doit(debug => 0);
		my $timetaken = Time::HiRes::tv_interval($start);

		$logger->info("$script_name completed in $timetaken seconds");
	} catch Error with {
		my $msg = shift;
		$logger->error("$msg: ", $msg->stacktrace());
		if($buffercache) {
			$buffercache->clear();
		}
	};

	$request->Finish();
	$handling_request = 0;
	if($exit_requested) {
		last;
	}
	if($ENV{SCRIPT_FILENAME}) {
		if(-M $ENV{SCRIPT_FILENAME} < 0) {
			last;
		}
	}
}

$logger->info("Shutting down");
if($buffercache) {
	$buffercache->purge();
}
CHI->stats->flush();
Log::WarnDie->dispatcher(undef);
exit(0);

sub doit
{
	CGI::Info->reset();

	$logger->debug('In doit - domain is ', $info->domain_name());

	my %params = (ref($_[0]) eq 'HASH') ? %{$_[0]} : @_;
	$config ||= PDS::Config->new({ logger => $logger, info => $info, debug => $params{'debug'} });
	$infocache ||= create_memory_cache(config => $config, logger => $logger, namespace => 'CGI::Info');

	my $options = {
		cache => $infocache,
		logger => $logger
	};

	my $syslog;
	if($syslog = $config->syslog()) {
		if($syslog->{'server'}) {
			$syslog->{'host'} = delete $syslog->{'server'};
		}
		$options->{'syslog'} = $syslog;
	}
	$info = CGI::Info->new($options);

	if(!defined($info->param('page'))) {
		$logger->info('No page given in ', $info->as_string());
		choose();
		return;
	}

	$linguacache ||= create_memory_cache(config => $config, logger => $logger, namespace => 'CGI::Lingua');
	my $lingua = CGI::Lingua->new({
		supported => [ 'en-gb' ],
		cache => $linguacache,
		info => $info,
		logger => $logger,
		debug => $params{'debug'},
		syslog => $syslog,
	});

	$vwflog ||= $config->vwflog() || File::Spec->catfile($info->logdir(), 'vwf.log');

	my $warnings = '';
	if(my $w = $info->warnings()) {
		my @warnings = map { $_->{'warning'} } @{$w};
		$warnings = join(';', @warnings);
	}

	if(!-r $vwflog) {
		# First run - put in the heading row
		open(my $log, '>', $vwflog);
		print $log '"domain_name","time","IP","country","type","language","http_code","template","args","warnings","error"',
			"\n";
		close $log;
	}

	# Access control checks
	if($ENV{'REMOTE_ADDR'} && $acl->all_denied(lingua => $lingua)) {
		print "Status: 403 Forbidden\n",
			"Content-type: text/plain\n",
			"Pragma: no-cache\n\n";

		unless($ENV{'REQUEST_METHOD'} && ($ENV{'REQUEST_METHOD'} eq 'HEAD')) {
			print "Access Denied\n";
		}
		$logger->info($ENV{'REMOTE_ADDR'}, ': access denied');
		$info->status(403);
		if($vwflog && open(my $fout, '>>', $vwflog)) {
			print $fout
				'"', $info->domain_name(), '",',
				'"', strftime('%F %T', localtime), '",',
				'"', ($ENV{REMOTE_ADDR} ? $ENV{REMOTE_ADDR} : ''), '",',
				'"', $lingua->country(), '",',
				'"', $info->browser_type(), '",',
				'"', $lingua->language(), '",',
				'403,',
				'"",',
				'"', $info->as_string(), '",',
				'"', $warnings, '"',
				"\n";
			close($fout);
		}
		return;
	}

	my $args = {
		info => $info,
		optimise_content => 1,
		logger => $logger,
		lint_content => $info->param('lint_content') // $params{'debug'},
		lingua => $lingua
	};

	if((!$info->is_search_engine()) && $config->root_dir() &&
	   ($info->param('page') ne 'home') &&
	   ((!defined($info->param('action'))) || ($info->param('action') ne 'send'))) {
		$args->{'save_to'} = {
			directory => File::Spec->catfile($config->root_dir(), 'save_to'),
			ttl => 3600 * 24,
			create_table => 1
		};
	}

	my $fb = FCGI::Buffer->new()->init($args);

	my $cachedir = $params{'cachedir'} || $config->{disc_cache}->{root_dir} || File::Spec->catfile($tmpdir, 'cache');

	if($fb->can_cache()) {
		$buffercache ||= create_disc_cache(config => $config, logger => $logger, namespace => $script_name, root_dir => $cachedir);
		$fb->init(
			cache => $buffercache,
			# generate_304 => 0,
			cache_duration => '1 day',
		);
		if($fb->is_cached()) {
			return;
		}
	}

	my $display;
	my $invalidpage;
	my $log = Class::Simple->new();

	$args = {
		cachedir => $cachedir,
		info => $info,
		logger => $logger,
		lingua => $lingua,
		config => $config,
		log => $log
	};

	# Display the requested page
	eval {
		my $page = $info->param('page');
		$page =~ s/#.*$//;

		$display = do {
			my $class = "PDS::Display::$page";
			eval { $class->new($args) };
		};
		if(!defined($display)) {
			$logger->info("Unknown page $page");
			$invalidpage = 1;
		} elsif(!$display->can('as_string')) {
			$logger->warn("Problem understanding $page");
			undef $display;
		}
	};

	my $error = $@;
	if($error) {
		$logger->error($error);
		$display = undef;
	}

	if(defined($display)) {
		# Pass in handles to the databases
		print $display->as_string({
			cachedir => $cachedir,
			databasedir => $database_dir,
			database_dir => $database_dir,
			albums => $albums,
			sections => $sections,
			photographs => $photographs,
		});
		if($vwflog && open(my $fout, '>>', $vwflog)) {
			print $fout
				'"', $info->domain_name(), '",',
				'"', strftime('%F %T', localtime), '",',
				'"', ($ENV{REMOTE_ADDR} ? $ENV{REMOTE_ADDR} : ''), '",',
				'"', $lingua->country(), '",',
				'"', $info->browser_type(), '",',
				'"', $lingua->language(), '",',
				$info->status(), ',',
				'"', ($log->template() ? $log->template() : ''), '",',
				'"', $info->as_string(), '",',
				'"', $warnings, '"',
				"\n";
			close($fout);
		}
	} elsif($invalidpage) {
		choose();
		if($vwflog && open(my $fout, '>>', $vwflog)) {
			print $fout
				'"', $info->domain_name(), '",',
				'"', strftime('%F %T', localtime), '",',
				'"', ($ENV{REMOTE_ADDR} ? $ENV{REMOTE_ADDR} : ''), '",',
				'"', $lingua->country(), '",',
				'"', $info->browser_type(), '",',
				'"', $lingua->language(), '",',
				$info->status(), ',',
				'"",',
				'"', $info->as_string(), '",',
				'"', $warnings, '"',
				"\n";
			close($fout);
		}
		return;
	} else {
		$logger->debug('disabling cache');
		$fb->init(
			cache => undef,
		);
		# Handle errors gracefully
		if($error eq 'Unknown page to display') {
			print "Status: 400 Bad Request\n",
				"Content-type: text/plain\n",
				"Pragma: no-cache\n\n";

			unless($ENV{'REQUEST_METHOD'} && ($ENV{'REQUEST_METHOD'} eq 'HEAD')) {
				print "I don't know what you want me to display.\n";
			}
			$info->status(400);
			$log->status(400);
		} elsif($error =~ /Can\'t locate .* in \@INC/) {
			$logger->error($error);
			print "Status: 500 Internal Server Error\n",
				"Content-type: text/plain\n",
				"Pragma: no-cache\n\n";

			unless($ENV{'REQUEST_METHOD'} && ($ENV{'REQUEST_METHOD'} eq 'HEAD')) {
				print "Software error - contact the webmaster\n",
					"$error\n";
			}
			$info->status(500);
			$log->status(500);
		} else {
			# No permission to show this page
			print "Status: 403 Forbidden\n",
				"Content-type: text/plain\n",
				"Pragma: no-cache\n\n";

			unless($ENV{'REQUEST_METHOD'} && ($ENV{'REQUEST_METHOD'} eq 'HEAD')) {
				print "Access Denied\n";
			}
			$info->status(403);
			$log->status(403);
		}
		if($vwflog && open(my $fout, '>>', $vwflog)) {
			print $fout
				'"', $info->domain_name(), '",',
				'"', strftime('%F %T', localtime), '",',
				'"', ($ENV{REMOTE_ADDR} ? $ENV{REMOTE_ADDR} : ''), '",',
				'"', $lingua->country(), '",',
				'"', $info->browser_type(), '",',
				'"', $lingua->language(), '",',
				$info->status(), ',',
				'"",',
				'"', $info->as_string(), '",',
				'"', $warnings, '"',
				"\n";
			close($fout);
		}
		throw Error::Simple($error ? $error : $info->as_string());
	}
}

sub choose
{
	$logger->info('Called with no page to display');

	my $status = $info->status();

	if($status != 200) {
		require HTTP::Status;
		HTTP::Status->import();

		print "Status: $status ",
			HTTP::Status::status_message($status),
			"\n\n";
		return;
	}

	print "Status: 300 Multiple Choices\n",
		"Content-type: text/plain\n";

	$info->status(300);

	# Print last modified date if path is defined
	if(my $path = $info->script_path()) {
		require HTTP::Date;
		HTTP::Date->import();

		my @statb = stat($path);
		my $mtime = $statb[9];
		print 'Last-Modified: ', HTTP::Date::time2str($mtime), "\n";
	}

	print "\n";

	# Print available pages unless it's a HEAD request
	unless($ENV{'REQUEST_METHOD'} && ($ENV{'REQUEST_METHOD'} eq 'HEAD')) {
		print "/cgi-bin/page.fcgi?page=albums\n",
			"/cgi-bin/page.fcgi?page=sections\n",
			"/cgi-bin/page.fcgi?page=photographs\n",
			"/cgi-bin/page.fcgi?page=upload\n",
			"/cgi-bin/page.fcgi?page=meta_data\n";
	}
}

# Is this client trying to attack us?
sub blacklist
{
	if(my $remote = $ENV{'REMOTE_ADDR'}) {
		if($blacklisted_ip{$remote}) {
			$info->status(301);
			return 1;
		}

		my $info = shift;
		if(my $string = $info->as_string()) {
			if(($string =~ /SELECT.+AND.+/) || ($string =~ /ORDER BY /) || ($string =~ / OR NOT /) || ($string =~ / AND \d+=\d+/) || ($string =~ /THEN.+ELSE.+END/) || ($string =~ /.+AND.+SELECT.+/) || ($string =~ /\sAND\s.+\sAND\s/) || ($string =~ /AND\sCASE\sWHEN/)) {
				$blacklisted_ip{$remote} = 1;
				$info->status(301);
				return 1;
			}
		}
	}
	return 0;
}

# False positives we don't need in the logs
sub filter
{
	# return 0 if($_[0] =~ /Can't locate Net\/OAuth\/V1_0A\/ProtectedResourceRequest.pm in /);
	# return 0 if($_[0] =~ /Can't locate auto\/NetAddr\/IP\/InetBase\/AF_INET6.al in /);
	# return 0 if($_[0] =~ /S_IFFIFO is not a valid Fcntl macro at /);

	return 0 if $_[0] =~ /Can't locate (Net\/OAuth\/V1_0A\/ProtectedResourceRequest\.pm|auto\/NetAddr\/IP\/InetBase\/AF_INET6\.al) in |
		   S_IFFIFO is not a valid Fcntl macro at /x;
	return 1;
}
