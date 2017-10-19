# ======================================================================
#
# Perl Source File
#
# NAME			: iiscfg.pl
#
# AUTHOR		: Thomas Keegan
# DATE  		: 7/25/2001
# LAST REVISED	: 11/11/2001
#
# PURPOSE		: Configures IIS for IDS
#
# THINGS TO DO	:
#   	Detect IIS Version 					(Done 7/27/2001)
#   	Automatically backup metabase		(Done 7/27/2001)
# 		Set file permissions
# 		Add script maps						(Done 7/27/2001)
# 		Allow choice of sites to create /ids dir under
# 		Hook into PPM and add modules
# 		Modify ids scripts for win32 compatibility
#   	Undo functionality
# ======================================================================

# Includes
use Cwd;
use Win32;
use Win32::OLE;
use Win32::OLE::Enum;
use Win32::TieRegistry( Delimiter=>"/");
#use Win32::NetAdmin;
#use Win32::FileSecurity;

# Declarations

        $WEB = 'ids';
        $DOMAIN = 'ids';
        $ipaddress = '';
        $hostheader = '';
        $idsdir = 'ids';
        $admindir = 'admin';
        $commentdir = 'postcomment';
        $perlloc = 'C:\Perl\bin\perl.exe';
        $perlswitches = ' "%s" %s'; 
        $idsdirmode = 0;
        $idsdedmode = 0; 

# PsudoConstants

	# Use InProc = 0 to run Web in Common Memory Space
	#						1 for Isolated
	#						2 for Pooled	(IIS 5 Only)
	
	# Detect IIS Version.
	$iisKey=$Registry->{"LMachine/System/CurrentControlSet/Services/W3SVC/Parameters"};
	$iisVer= $iisKey->{"/MajorVersion"};
	
	if (iisVer == "0x00000005") {
		$InProc     = '2';
		}
	else {
		$InProc     = '1';
		}
	

	# Debug Mode: Use 0 for 0ff, 1 for On
	$debug		= '0';
	
	# Default Website index number
	$defaultindex = '1';

	#Metabase locations
	$WebRootNodePath = 'IIS://localhost/W3SVC';
	$RootNodePath = 'IIS://localhost';

# Interview
	$WebRoot = cwd();
	$WebRoot =~ s/\//\\/gis;
	
	print "This script will ask several questions, and then configure IIS to run IDS.\n";
	print "If you do not know the answer to a question, hit return to use the default.\n";
	print "WARNING: This script will modify the metabase. Please make a backup first!\n";
	print "On Windows NT or Windows 2000, you must be logged in as an administrator.\n";
	print "Do you want to configure IDS as a directory, a dedicated website, or both?\n";

	until (($idsdirmode eq TRUE) or ($idsdedmode eq TRUE)){
		print "You must choose at least one option.\n";
		print "       Configure IDS as a directory? (IDS is at http://sitename/ids) [y]: ";
			$input = <STDIN>;
			chomp $input;
	
		if ($input eq '' or $input eq 'y'){
			$idsdirmode = TRUE;}
		else {
			$idsdirmode = 0;}
		
		print "\n       Configure IDS as a dedicated website? (IDS is at http://sitename) [y]: ";
			$input = <STDIN>;
			chomp $input;
	
		if (($input eq '') or ($input eq 'y')){
			$idsdedmode = TRUE;}
		else {
			$idsdedmode = 0;}
		
		if ($idsdirmode) {print "\nIDS will be configured as a directory.\n";} 
		if ($idsdedmode) {print "\nIDS will be configured as a dedicated site.\n";} 
		
	}


	print "Enter the current directory, [$WebRoot]: ";
		$input = <STDIN>;
		chomp $input;
	
	if ($input ne ''){
		print "$input\n";
		$WebRoot = $input;
		}
	
	print "Using $WebRoot\n";
	
	print "Enter the full path to perl.exe [$perlloc]: ";
		$input = <STDIN>;
		chomp $input;
	
	if ($input ne ''){
		print "$input\n";
		$perlloc = $input;
		}
	
	print "Using $perlloc\n";
	
	if ($idsdedmode) {
		print "Enter IP Address [All Unassigned]: ";
			$input = <STDIN>;
			chomp $input;
		
		if ($input ne ''){
		print "$input\n";
		$ipaddress = $input;
		}
	
		print "Enter host header [none]: ";
			$input = <STDIN>;
			chomp $input;
	
		if ($input ne ''){
		print "$input\n";
		$hostheader = $input;
		}
		
		print "Do you want to start this new site? [n]: ";
			$input = <STDIN>;
			chomp $input;
	
		if ($input eq '' or $input eq 'n'){
			$idsstartsite = 0;}
		else {
			$idsstartsite = TRUE;}
	
	}
	
	

#$idsdedmode = '0';
#$idsdirmode = '0';

# SubMain

	#backup metabase
	backupmetabase ($RootNodePath);

	#loading metabase into array
	webmetabase ();

	if ($idsdedmode) {
		# Need to create a new web site.
		$nextindex = findindex();
		$newsite = newweb($WebRootNodePath, $nextindex, $ipaddress, $hostheader, $DOMAIN, $WebRoot);
	
		# Create the Admin Virtual Directory
	 	$newdir = CreateVirDir($WebRootNodePath.'/'.$nextindex.'/ROOT', $admindir, $WebRoot."\\".$admindir);
 		
 		# Configure this virtual directory
 		my $confDir = Win32::OLE->GetObject($WebRootNodePath.'/'.$nextindex.'/ROOT/'.$admindir) or  
		die "can't open metabase path";
			$confDir->{AccessRead} = True;
	      	$confDir->{AccessScript} = True;
	      	$confDir->{AccessExecute} = True;
	      	$confDir->{AuthAnonymous} = False;
			$confDir->{AuthBasic} = True;
	      	$confDir->AppCreate2($InProc); 	      	
			$confDir->{AppFriendlyName} = "Admin Interface for IDS";
			$confDir->{DefaultDoc} = "index.cgi";
			$confDir->{EnableDefaultDoc} = True;
 		 	$confDir->SetInfo;
 	
 		# Create the Comment Virtual Directory
 		$newdir = CreateVirDir($WebRootNodePath.'/'.$nextindex.'/ROOT', $commentdir, $WebRoot."\\".$commentdir);
 		
 		# Configure this virtual directory
 		my $confDir = Win32::OLE->GetObject($WebRootNodePath.'/'.$nextindex.'/ROOT/'.$commentdir) or  
		die "can't open metabase path";
 			$confDir->{AccessRead} = True;
	      	$confDir->{AccessScript} = True;
	      	$confDir->{AccessExecute} = True;
	      	$confDir->{AuthAnonymous} = True;
			$confDir->{AuthBasic} = True;
	      	$confDir->AppCreate2($InProc); 	      	
			$confDir->{AppFriendlyName} = "IDS comments";
			$confDir->{DefaultDoc} = "index.cgi";	
	 		$confDir->{EnableDefaultDoc} = True;
 		 	$confDir->SetInfo;
	
	}

	if ($idsdirmode) {
	$nextindex = $defaultindex;
	
	# Create the IDS Virtual Directory
   	$newdir = CreateVirDir($WebRootNodePath.'/'.$nextindex.'/ROOT', $idsdir, $WebRoot);
 	
 	#Configure this virtual directory
 	my $confDir = Win32::OLE->GetObject($WebRootNodePath.'/'.$nextindex.'/ROOT/'.$idsdir) or  
		die "can't open metabase path";
			$confDir->{AccessRead} = True;
	      	$confDir->{AccessScript} = True;
	      	$confDir->{AccessExecute} = True;
	      	$confDir->{AuthAnonymous} = True;
			$confDir->{AuthBasic} = True;
	      	$confDir->AppCreate2($InProc); 	      	
			$confDir->{AppFriendlyName} = "Image Display System";
			$confDir->{DefaultDoc} = "index.cgi";	
	 		$confDir->{EnableDefaultDoc} = True;
	 		$confDir->{ScriptMaps} = ".cgi,$perlloc$perlswitches,4,GET,HEAD,POST";
 		 	$confDir->SetInfo;
 		 	
 		 # Create the Admin Virtual Directory	 	
 		$newdir = CreateVirDir($WebRootNodePath.'/'.$nextindex.'/ROOT/'.$idsdir, $admindir, $WebRoot."\\".$admindir);
 		
 		# Configure this virtual directory
 		my $confDir = Win32::OLE->GetObject($WebRootNodePath.'/'.$nextindex.'/ROOT/'.$idsdir.'/'.$admindir) or  
		die "can't open metabase path";
			$confDir->{AccessRead} = True;
	      	$confDir->{AccessScript} = True;
	      	$confDir->{AccessExecute} = True;
	      	$confDir->{AuthAnonymous} = False;
			$confDir->{AuthBasic} = True;
	      	$confDir->AppCreate2($InProc); 	      	
			$confDir->{AppFriendlyName} = "Admin Interface for IDS";
			$confDir->{DefaultDoc} = "index.cgi";
			$confDir->{EnableDefaultDoc} = True;
	 		$confDir->SetInfo;
 	
 	
 		# Create the Comment Virtual Directory
 		$newdir = CreateVirDir($WebRootNodePath.'/'.$nextindex.'/ROOT/'.$idsdir, $commentdir, $WebRoot."\\".$commentdir);
 		
 		#Configure this virtual directory
 		my $confDir = Win32::OLE->GetObject($WebRootNodePath.'/'.$nextindex.'/ROOT/'.$idsdir.'/'.$commentdir) or  
		die "can't open metabase path";
			$confDir->{AccessRead} = True;
	      	$confDir->{AccessScript} = True;
	      	$confDir->{AccessExecute} = True;
	      	$confDir->{AuthAnonymous} = True;
			$confDir->{AuthBasic} = True;
	      	$confDir->AppCreate2($InProc); 	      	
			$confDir->{AppFriendlyName} = "IDS comments";
			$confDir->{DefaultDoc} = "index.cgi";	
	 		$confDir->{EnableDefaultDoc} = True;
 		 	$confDir->SetInfo;
 		 	
			}
	




# Functions and Subs

sub webmetabase {          
    # Subroutine used for loading all existing web servers
	print "Loading Web Service Metabase.......\n\n";

   	#Assigning Web service object
	my $obj = Win32::OLE->GetObject($WebRootNodePath) or  
	die "can't open service";

   	my $children = Win32::OLE::Enum->new($obj); 	#objects contained in Web Service

	my $z = 1;
	$counter = 0;
	foreach my $node ($children->All) {
		if ($debug) {print "Index       = $node->{Name}\n";}
		                ($index[$z]) = ($node->Name);
	                $z++;
	                $counter++;
		}
               $node = "";

}

sub findindex {
               ##Subroutine to find next available index for web.
               print "Finding Index for Web....\n";
	my $y = 1;
	while ($y < 300) {
	    my $z = 1;
	    my $counter3 = 0;
	    while ($index[$z] ne ()) {
	     	if ($debug) {print "%-2s %-2s\n", $y,$index[$z];}

	        if ($y != $index[$z] ) {
	           $counter3++;
	        }
        	if ($counter3 == $counter) {
	 	       $findindex = $y;
	 	       return $findindex;
	 	       $z = 301;
	 	       $y = 301;
	 	   } 
		   $z++;
		}
	     $y++;
	}
}

#This subroutine creates a new site

	sub newweb {
	        print "Creating Web Server.....\n";
		my ($MetabasePath, $Index, $ipaddress, $hostheader, $ServerComment, $RootDirectory) = @_;
		print $ipaddress $hostheader."\n";
		print "Metabase Path = $MetabasePath\n";
		print "Index         = $Index\n";
		 
		my $obj = Win32::OLE->GetObject($MetabasePath) or  
			die "can't open metabase path";
		
		
		my $NewWebServer = $obj->Create("IIsWebServer", $Index) or  
			die "can't create new web server";
			
			$BindingString = ($ipaddress.":80:".$hostheader);
			
			$NewWebServer->{ServerBindings} = $BindingString;
			$NewWebServer->{ServerComment} = $ServerComment;
			$NewWebServer->{KeyType} = "IIsWebServer";
			$NewWebServer->{LogType} = 1;
		    $NewWebServer->{LogPluginClsid} = "{FF160663-DE82-11CF-BC0A-00AA006111E0}";
			$NewWebServer->{LogExtFileFlags} = 1048575;
		    $NewWebServer->{AuthFlags} = 3;
		    $NewWebServer->{EnableDirBrowsing} = False;
		    $NewWebServer->{DefaultDoc} = "index.cgi";
			$NewWebServer->{EnableDefaultDoc} = True;
			$NewWebServer->{ScriptMaps} = ".cgi,$perlloc$perlswitches,4,GET,HEAD,POST";
		$NewWebServer->SetInfo;
		
		
		my $NewDir = $NewWebServer->Create("IIsWebVirtualDir", "ROOT") or
			   die "can't create virtual root";
				$NewDir->{Path} = $RootDirectory;
				$NewDir->{AccessRead} = true;
                $NewDir->{AccessScript} = True;
                $NewDir->{AccessExecute} = True;
               	$NewDir->AppCreate2($InProc);
    			$NewDir->{AppFriendlyName} = $ServerComment;
				$NewDir->{AuthAnonymous} = True;
				$NewDir->{AuthBasic} = True;
			$NewDir->SetInfo;

			if ($idsstartsite) {
 	        	$NewWebServer->Start;
 	        	}
	             }

	sub CreateVirDir {
	        print "Creating Virtual Directory.....\n";
		my ($MetabasePath, $VirtualDirectoryName, $PhysicalDirectoryName) = @_;
		
		my $obj = Win32::OLE->GetObject($MetabasePath) or  
		die "can't open metabase path";
		
		my $NewVDir = $obj->Create("IIsWebVirtualDir", $VirtualDirectoryName) or
			   die "can't create virtual root";	
	
		$NewVDir->{Path} = $PhysicalDirectoryName;
		$NewVDir->SetInfo;
	}

	sub backupmetabase {
		print "Backing up Metabase to pre_ids_conf\n";
		my ($MetabasePath) = @_;
		my $flags = (MD_BACKUP_SAVE_FIRST or MD_BACKUP_FORCE_BACKUP);
		
		
		my $obj = Win32::OLE->GetObject($MetabasePath) or  
		die "can't open metabase path";
		
		$obj->Backup("pre_ids_conf", -1, 1);
		print "Metabase Backed Up\n";
	}