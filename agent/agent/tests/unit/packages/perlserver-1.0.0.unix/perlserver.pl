#!/usr/bin/perl

use HTTP::Daemon;
use HTTP::Status;

my $d = new HTTP::Daemon;
print $d->url . "\n";
$d->url =~ /.*:([0-9]*)/;
open(PORT, ">port") || die("Can't open file port");
print "got here $1: " . $d->url . "\n";
print PORT $1;
close(PORT);

while (my $c = $d->accept) {
    while (my $r = $c->get_request) {
        if ($r->method eq 'GET') {
            # remember, this is *not* recommened practice :-)
            $c->send_file_response("got_here.xml");
        }
    }            

    $c->close;
    undef($c);
}
