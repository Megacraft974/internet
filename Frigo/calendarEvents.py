import caldav

url = "webcal://p51-caldav.icloud.com/published/2/MTA1MTc4OTU3OTYxMDUxN2_lVtyur1xTe0YJLaE7tYbDPpBaomGHjoBp1-u5Hlen"
username = "william.michaud974@icloud.com"
password = "Megacraft974"

client = caldav.DAVClient(url=url, username=username, password=password)
my_principal = client.principal()
calendars = my_principal.calendars()

if calendars:
    ## Some calendar servers will include all calendars you have
    ## access to in this list, and not only the calendars owned by
    ## this principal.  TODO: see if it's possible to find a list of
    ## calendars one has access to.
    print("your principal has %i calendars:" % len(calendars))
    for c in calendars:
        print("    Name: %-20s  URL: %s" % (c.name, c.url))
else:
    print("your principal has no calendars")
