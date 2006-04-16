SUBDIRS = 

PKGNAME = sbdmock
VERSION=$(shell awk '/__VERSION__ = / { print $$3 }' sbdmock.py)

all: subdirs

clean:
	rm -f *.pyc *.pyo *~ *.bak
	for d in $(SUBDIRS); do make -C $$d clean ; done

distclean: clean
	rm -rf dist build
	rm *.tar.gz

subdirs:
	for d in $(SUBDIRS); do make -C $$d; [ $$? = 0 ] || exit 1 ; done

install:
	mkdir -p $(DESTDIR)/usr/bin/
	install -m 755 sbdarchtarget.py $(DESTDIR)/usr/bin/sbdarchtarget
	install -m 755 sbdmock.py $(DESTDIR)/usr/bin/sbdmock
	for d in $(SUBDIRS); do make  DESTDIR=`cd $(DESTDIR); pwd` -C $$d install; [ $$? = 0 ] || exit 1; done

archive:
	@rm -rf ${PKGNAME}-%{VERSION}.tar.gz
	@rm -rf /tmp/${PKGNAME}-$(VERSION) /tmp/${PKGNAME}
	@dir=$$PWD; cd /tmp; cp -a $$dir ${PKGNAME}
	@rm -rf /tmp/${PKGNAME}/${PKGNAME}-daily.spec /tmp/${PKGNAME}/build /tmp/${PKGNAME}/dist
	@mv /tmp/${PKGNAME} /tmp/${PKGNAME}-$(VERSION)
	@dir=$$PWD; cd /tmp; tar cvzf $$dir/${PKGNAME}-$(VERSION).tar.gz ${PKGNAME}-$(VERSION) --exclude=.svn --exclude=CVS
	@rm -rf /tmp/${PKGNAME}-$(VERSION)	
	@echo "The archive is in ${PKGNAME}-$(VERSION).tar.gz"
