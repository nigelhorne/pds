use PDS::Utils;

# See https://github.com/nigelhorne/CGI-Allow

package PDS::Allow;

# PDS is licensed under GPL2.0 for personal use only
# njh@bandsman.co.uk

# Decide if we're going to allow this client to view the website
# Usage:
#	unless(PDS::Allow::allow({info => $info, lingua => $lingua})) {

use strict;
use warnings;
use File::Spec;
use Carp;
use Error;

use constant DSHIELD => 'https://secure.dshield.org/api/sources/attacks/100/2012-03-08';

# TODO: Remove code duplicated with CGI::Allow
# Blacklist of country codes (hardcoded for now)
my %blacklist = map { $_ => 1 } qw(
	BG BR CN CO CY IN IR KR LT MA MD MX PK RS RU SA TR TW UY VE VN ZA
);

our %blacklist_agents = (
	'Barkrowler' => 'Barkrowler',
	'masscan' => 'Masscan',
	'python-requests/2.27.1' => 'python-requests/2.27.1',
	'WBSearchBot' => 'Warebay',
	'MJ12' => 'Majestic',
	'Mozilla/4.0 (compatible; Vagabondo/4.0; webcrawler at wise-guys dot nl; http://webagent.wise-guys.nl/; http://www.wise-guys.nl/)' => 'wise-guys',
	'Mozilla/5.0 zgrab/0.x' => 'zgrab',
	'Mozilla/5.0 (compatible; IODC-Odysseus Survey 21796-100-051215155936-107; +https://iodc.co.uk)' => 'iodc',
	'Mozilla/5.0 (compatible; adscanner/)' => 'adscanner',
	'Mozilla/5.0 (compatible; SemrushBot/6~bl; +http://www.semrush.com/bot.html)' => 'SemrushBot',
	'ZoominfoBot (zoominfobot at zoominfo dot com)' => 'zoominfobot',
);

our %status;

sub allow {
	my $addr = $ENV{'REMOTE_ADDR'};

	if(!defined($addr)) {
		# Not running as a CGI
		return 1;
	}

	my %args = (ref($_[0]) eq 'HASH') ? %{$_[0]} : @_;

	my $logger = $args{'logger'};

	if(defined($status{$addr})) {
		# Cache the value
		if($logger) {
			$logger->debug("$addr: cached value ", $status{$addr});
		}
		return $status{$addr};
	}
	if($logger) {
		$logger->trace('In ', __PACKAGE__);
	}

	if($ENV{'HTTP_USER_AGENT'}) {
		if(my $blocked = $blacklist_agents{$ENV{'HTTP_USER_AGENT'}}) {
			if($logger) {
				$logger->info("$blocked blacklisted");
			}
			$status{$addr} = 0;
			throw Error::Simple("$addr: $blocked is blacklisted", 1);
		}
	}

	my $info = $args{'info'};
	if(!defined($info)) {
		if($logger) {
			$logger->warn('Info not given');
		} else {
			carp('Info not given');
		}
		$status{$addr} = 1;
		return 1;
	}

	unless($info->is_search_engine()) {
		require Data::Throttler;
		Data::Throttler->import();

		# Handle YAML Errors
		my $db_file = File::Spec->catfile($info->tmpdir(), 'throttle');
		eval {
			my $throttler = Data::Throttler->new(
				max_items => 15,
				interval => 90,
				backend => 'YAML',
				backend_options => {
					db_file => $db_file
				}
			);

			unless($throttler->try_push(key => $addr)) {
				# Recommend you send HTTP 429 at this point
				if($logger) {
					$logger->warn("$addr has been throttled");
				}
				$status{$addr} = 0;
				throw Error::Simple("$addr has been throttled");
			}
		};
		if($@) {
			if($logger) {
				$logger->debug("removing $db_file");
			}
			unlink($db_file);
		}

		unless(($addr =~ /^192\.168\./) || $info->baidu()) {
			my $lingua = $args{'lingua'};
			if(defined($lingua) && $lingua->country() && $blacklist_countries{uc($lingua->country())}) {
				if($logger) {
					$logger->warn("$addr blocked connexion from ", $lingua->country());
				}
				$status{$addr} = 0;
				$info->status(403);
				throw Error::Simple("$addr: blocked connexion from " . $lingua->country(), 0);
			}
		}

		if(defined($ENV{'REQUEST_METHOD'}) && ($ENV{'REQUEST_METHOD'} eq 'GET')) {
			my $params = $info->params();
			if(defined($params) && scalar(%{$params})) {
				require CGI::IDS;
				CGI::IDS->import();

				my $ids = CGI::IDS->new();
				$ids->set_scan_keys(scan_keys => 1);
				my $impact = $ids->detect_attacks(request => $params);
				if($impact > 0) {
					if($logger) {
						$logger->warn("$addr: IDS blocked connexion for ", $info->as_string(), " impact = $impact");
						$logger->warn(Data::Dumper->new([$ids->get_attacks()]));
					}
					if($impact > 30) {
						$status{$addr} = 0;
						$info->status(403);
						throw Error::Simple("$addr: IDS blocked connexion for " . $info->as_string());
					}
				}

				foreach my $v (values %{$params}) {
					if($v eq '/etc/passwd') {
						if($logger) {
							$logger->warn("$addr: blocked connexion attempt for /etc/passwd from ", $info->as_string());
						}
						$status{$addr} = 0;
						$info->status(403);
						return 0;
					}
				}
			}
		}

		if(my $referer = $ENV{'HTTP_REFERER'}) {
			$referer =~ tr/ /+/;	# FIXME - this shouldn't be happening

			if(($referer =~ /^http:\/\/keywords-monitoring-your-success.com\/try.php/) ||
			   ($referer =~ /^http:\/\/www.tcsindustry\.com\//) ||
			   ($referer =~ /^http:\/\/free-video-tool.com\//)) {
				if($logger) {
					$logger->warn("$addr: Blocked trawler");
				}
				$info->status(403);
				$status{$addr} = 0;
				throw Error::Simple("$addr: Blocked trawler");
			}

			# Protect against Shellshocker
			require Data::Validate::URI;
			Data::Validate::URI->import();

			unless(Data::Validate::URI->new()->is_uri($referer)) {
				if($logger) {
					$logger->warn("$addr: Blocked shellshocker for $referer");
				}
				$status{$addr} = 0;
				$info->status(403);
				throw Error::Simple("$addr: Blocked shellshocker for $referer");
			}
		}

		if(my $script_uri = $ENV{'SCRIPT_URI'}) {
			if(($script_uri =~ /\/shell\.php$/) ||
			   ($script_uri =~ /\/cmd\.php$/)) {
				if($logger) {
					$logger->warn("$addr: Blocked attacker from $addr");
				}
				$status{$addr} = 0;
				throw Error::Simple("$addr: Blocked attacker for $addr");
			}
		}
	}

	require DateTime;
	DateTime->import();

	my @ips;
	my $today = DateTime->today()->ymd();
	my $readfromcache;

	my $cache = $args{'cache'};
	if(!defined($cache)) {
		throw Error::Simple('Either cache or config must be given') unless($args{config});
		$cache = ::create_memory_cache(config => $args{'config'}, namespace => __PACKAGE__, logger => $logger);
	}
	if(defined($cache)) {
		my $cachecontent = $cache->get($today);
		if($cachecontent) {
			if($logger) {
				$logger->debug("read from cache $cachecontent");
			}
			@ips = split(/,/, $cachecontent);
			if($ips[0]) {
				$readfromcache = 1;
			} else {
				if($logger) {
					$logger->info("DShield cache for $today is empty, deleting to force reread");
				}
				$cache->remove($today);
			}
		} elsif($logger) {
			$logger->debug("Can't find $today in the cache");
		}
	} elsif($logger) {
		$logger->warn('Couldn\'t create the DShield cache');
	}

	unless($ips[0]) {
		require LWP::Simple::WithCache;
		LWP::Simple::WithCache->import();
		require XML::LibXML;
		XML::LibXML->import();

		if($logger) {
			$logger->trace('Downloading DShield signatures');
		}

		my $xml;
		eval {
			if(my $string = LWP::Simple::WithCache::get(DSHIELD)) {
				$xml = XML::LibXML->load_xml(string => $string);
                        } elsif($logger) {
                                $logger->warn("Couldn't download ", DSHIELD);
                                delete $status{$addr};
                                return 1;
                        } else {
                                warn DSHIELD;
                                delete $status{$addr};
                                return 1;
                        }
		};
		unless($@ || !defined($xml)) {
			foreach my $source ($xml->findnodes('/sources/data')) {
				my $lastseen = $source->findnodes('./lastseen')->to_literal();
				next if($readfromcache && ($lastseen ne $today));	# FIXME: Should be today or yesterday to avoid midnight rush
				my $ip = $source->findnodes('./ip')->to_literal();
				$ip =~ s/0*(\d+)/$1/g;	# Perl interprets numbers leading with 0 as octal
				push @ips, $ip;
			}
			if(defined($cache) && $ips[0] && !$readfromcache) {
				my $cachecontent = join(',', @ips);
				if($logger) {
					$logger->info("Setting DShield cache for $today to $cachecontent");
				}
				$cache->set($today, $cachecontent, '1 day');
			}
		}
	}

	# FIXME: Doesn't realise 1.2.3.4 is the same as 001.002.003.004
	if(grep($_ eq $addr, @ips)) {
		if($logger) {
			$logger->warn("Dshield blocked connexion from $addr");
		}
		$status{$addr} = 0;
		throw Error::Simple("Dshield blocked connexion from $addr");
	}

	if($info->get_cookie(cookie_name => 'mycustomtrackid')) {
		if($logger) {
			$logger->warn('Blocking possible jqic');
		}
		$status{$addr} = 0;
		throw Error::Simple('Blocking possible jqic');
	}

	if($logger) {
		$logger->trace("Allowing connexion from $addr");
	}

	$status{$addr} = 1;
	return 1;
}

1;
