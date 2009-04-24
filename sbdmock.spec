Name:           sbdmock
Version:        0.4.2
Release:        1%{?dist}
Summary:        Scratchbox debian package builder

Group:          Development/Languages
License:        GPL
URL:            http://bifh.org/wiki/sbdmock
Source0:        %{name}-%{version}.tar.gz
Requires:       python-minideblib
Requires:       scratchbox-core >= 1.0.8
BuildRoot:      %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)

BuildArch:      noarch
BuildRequires:  python-devel



%description
Small python script for building debian packages using Scratchbox 

%prep
%setup -q 

%build
# Remove CFLAGS=... for noarch packages (unneeded)
CFLAGS="$RPM_OPT_FLAGS" %{__python} setup.py build


%install
rm -rf $RPM_BUILD_ROOT
%{__python} setup.py install -O1 --skip-build --root $RPM_BUILD_ROOT

# example configs
mkdir -p $RPM_BUILD_ROOT/%{_sysconfdir}/sbdmock
install -m 755 etc/*.cfg $RPM_BUILD_ROOT%{_sysconfdir}/sbdmock

%clean
rm -rf $RPM_BUILD_ROOT


%files
%defattr(-,root,root,-)
%doc README 
%{_bindir}/sbd*
%dir %{_sysconfdir}/sbdmock
%config(noreplace) %{_sysconfdir}/sbdmock/*.cfg


%changelog
* Fri Apr 24 2009 Alexandr D. Kanevskiy <packages@bifh.org>
- 0.4.2 release

* Sun Nov 11 2007 Alexandr D. Kanevskiy <packages@bifh.org>
- initial packaging 
