
# Resulting binary formats we want from iPXE
%global formats rom

# PCI IDs (vendor,product) of the ROMS we want for QEMU
#
#    pcnet32: 0x1022 0x2000
#   ne2k_pci: 0x10ec 0x8029
#      e1000: 0x8086 0x100e
#    rtl8139: 0x10ec 0x8139
# virtio-net: 0x1af4 0x1000
#   eepro100: 0x8086 0x1209
#     e1000e: 0x8086 0x10d3
#    vmxnet3: 0x15ad 0x07b0
%global qemuroms 10222000 10ec8029 8086100e 10ec8139 1af41000 80861209 808610d3 15ad07b0

# We only build the ROMs if on an x86 build host. The resulting
# binary RPM will be noarch, so other archs will still be able
# to use the binary ROMs.
#
# We do cross-compilation for 32->64-bit, but not for other arches
# because EDK II does not support big-endian hosts.
%global buildarches %{ix86} x86_64

# debugging firmwares does not go the same way as a normal program.
# moreover, all architectures providing debuginfo for a single noarch
# package is currently clashing in koji, so don't bother.
%global debug_package %{nil}

# Upstream don't do "releases" :-( So we're going to use the date
# as the version, and a GIT hash as the release. Generate new GIT
# snapshots using the folowing commands:
#
# $ hash=`git log -1 --format='%h'`
# $ date=`git log -1 --format='%cd' --date=short | tr -d -`
# $ git archive --prefix ipxe-${date}-git${hash}/ ${hash} | xz -7e > ipxe-${date}-git${hash}.tar.xz
#
# And then change these two:

%global gitcommit a8a1e4e2050d41195d448854240081813bdf72ad
%{?gitcommit:%global gitcommitshort %(c=%{gitcommit}; echo ${c:0:7})}
%global date 20170411

Name:    ipxe
Version: %{date}
Release: 1.git%{gitcommitshort}%{?dist}
Summary: A network boot loader

Group:   System Environment/Base
License: GPLv2 with additional permissions and BSD
URL:     http://ipxe.org/

Source0: https://git.ipxe.org/ipxe.git/snapshot/%{gitcommit}.tar.bz2

# Enable IPv6 for qemu's config
# Sent upstream: http://lists.ipxe.org/pipermail/ipxe-devel/2015-November/004494.html
Patch0001: 0001-build-Enable-IPv6-for-in-qemu-config.patch

Patch0002: 0002-enable-DOWNLOAD_PROTO_NFS.patch

BuildRequires: perl
BuildRequires: perl-Getopt-Long
BuildRequires: syslinux
BuildRequires: mtools
BuildRequires: mkisofs
BuildRequires: edk2-tools
BuildRequires: xz-devel

BuildRequires: binutils-devel
BuildRequires: binutils-x86_64-linux-gnu gcc-x86_64-linux-gnu

Obsoletes: gpxe <= 1.0.1

%package bootimgs
Summary: Network boot loader images in bootable USB, CD, floppy and GRUB formats
Group:   Development/Tools
BuildArch: noarch
Obsoletes: gpxe-bootimgs <= 1.0.1

%package roms
Summary: Network boot loader roms in .rom format
Group:  Development/Tools
Requires: %{name}-roms-qemu = %{version}-%{release}
BuildArch: noarch
Obsoletes: gpxe-roms <= 1.0.1

%package roms-qemu
Summary: Network boot loader roms supported by QEMU, .rom format
Group:  Development/Tools
BuildArch: noarch
Obsoletes: gpxe-roms-qemu <= 1.0.1

%description bootimgs
iPXE is an open source network bootloader. It provides a direct
replacement for proprietary PXE ROMs, with many extra features such as
DNS, HTTP, iSCSI, etc.

This package contains the iPXE boot images in USB, CD, floppy, and PXE
UNDI formats.

%description roms
iPXE is an open source network bootloader. It provides a direct
replacement for proprietary PXE ROMs, with many extra features such as
DNS, HTTP, iSCSI, etc.

This package contains the iPXE roms in .rom format.


%description roms-qemu
iPXE is an open source network bootloader. It provides a direct
replacement for proprietary PXE ROMs, with many extra features such as
DNS, HTTP, iSCSI, etc.

This package contains the iPXE ROMs for devices emulated by QEMU, in
.rom format.

%description
iPXE is an open source network bootloader. It provides a direct
replacement for proprietary PXE ROMs, with many extra features such as
DNS, HTTP, iSCSI, etc.

%prep
%setup -q -n %{name}-%{gitcommitshort}
%patch0001 -p1
%patch0001 -p1


%build
cd src

# ath9k drivers are too big for an Option ROM, and ipxe devs say it doesn't
# make sense anyways
# http://lists.ipxe.org/pipermail/ipxe-devel/2012-March/001290.html
rm -rf drivers/net/ath/ath9k

make_ipxe() {
    make %{?_smp_mflags} \
        NO_WERROR=1 V=1 \
        GITVERSION=%{gitcommitshort} \
        CROSS_COMPILE=x86_64-linux-gnu- \
        "$@"
}

make_ipxe bin-i386-efi/ipxe.efi bin-x86_64-efi/ipxe.efi

make_ipxe ISOLINUX_BIN=/usr/share/syslinux/isolinux.bin \
    bin/undionly.kpxe bin/ipxe.{dsk,iso,usb,lkrn} \
    allroms

# build roms with efi support for qemu
mkdir bin-combined
for rom in %{qemuroms}; do
  make_ipxe CONFIG=qemu bin/${rom}.rom
  make_ipxe CONFIG=qemu bin-i386-efi/${rom}.efidrv
  make_ipxe CONFIG=qemu bin-x86_64-efi/${rom}.efidrv
  vid="0x${rom%%????}"
  did="0x${rom#????}"
  EfiRom -f "$vid" -i "$did" --pci23 \
         -b  bin/${rom}.rom \
         -ec bin-i386-efi/${rom}.efidrv \
         -ec bin-x86_64-efi/${rom}.efidrv \
         -o  bin-combined/${rom}.rom
  EfiRom -d  bin-combined/${rom}.rom
done

%install
mkdir -p %{buildroot}/%{_datadir}/%{name}/
mkdir -p %{buildroot}/%{_datadir}/%{name}.efi/
pushd src/bin/

cp -a undionly.kpxe ipxe.{iso,usb,dsk,lkrn} %{buildroot}/%{_datadir}/%{name}/

for fmt in %{formats};do
 for img in *.${fmt};do
      if [ -e $img ]; then
   cp -a $img %{buildroot}/%{_datadir}/%{name}/
   echo %{_datadir}/%{name}/$img >> ../../${fmt}.list
  fi
 done
done
popd

cp -a src/bin-i386-efi/ipxe.efi %{buildroot}/%{_datadir}/%{name}/ipxe-i386.efi
cp -a src/bin-x86_64-efi/ipxe.efi %{buildroot}/%{_datadir}/%{name}/ipxe-x86_64.efi

# the roms supported by qemu will be packaged separatedly
# remove from the main rom list and add them to qemu.list
for fmt in rom ;do
 for rom in %{qemuroms} ; do
  sed -i -e "/\/${rom}.${fmt}/d" ${fmt}.list
  echo %{_datadir}/%{name}/${rom}.${fmt} >> qemu.${fmt}.list
 done
done
for rom in %{qemuroms}; do
  cp src/bin-combined/${rom}.rom %{buildroot}/%{_datadir}/%{name}.efi/
  echo %{_datadir}/%{name}.efi/${rom}.rom >> qemu.rom.list
done

%files bootimgs
%dir %{_datadir}/%{name}
%{_datadir}/%{name}/ipxe.iso
%{_datadir}/%{name}/ipxe.usb
%{_datadir}/%{name}/ipxe.dsk
%{_datadir}/%{name}/ipxe.lkrn
%{_datadir}/%{name}/ipxe-i386.efi
%{_datadir}/%{name}/ipxe-x86_64.efi
%{_datadir}/%{name}/undionly.kpxe
%doc COPYING COPYING.GPLv2 COPYING.UBDL

%files roms -f rom.list
%dir %{_datadir}/%{name}
%doc COPYING COPYING.GPLv2 COPYING.UBDL

%files roms-qemu -f qemu.rom.list
%dir %{_datadir}/%{name}
%dir %{_datadir}/%{name}.efi
%doc COPYING COPYING.GPLv2 COPYING.UBDL

%changelog
* Tue Apr 11 2017 Yu Watanabe <watanabe.yu@gmail.com> - 20170411-1.gita8a1e4e
- Update to latest git snapshot a8a1e4e2050d41195d448854240081813bdf72ad

* Thu Mar 23 2017 Yu Watanabe <watanabe.yu@gmail.com> - 20170322-1.git9ecad20
- Update to latest git snapshot 9ecad204fc8e55bc34ffb4b3ef8f19e57729308b

* Sun Mar 12 2017 Yu Watanabe <watanabe.yu@gmail.com> - 20170310-1.git553f485
- Update to latest git snapshot 553f4857346faa8c5f6ddf9eced4180924890bfc

* Sun Feb 12 2017 Yu Watanabe <watanabe.yu@gmail.com> - 20170207-1.git30f96c9
- Update to latest git snapshot 30f96c9f41f2596493c6ca18060bebaaaf44415b

* Fri Feb 10 2017 Fedora Release Engineering <releng@fedoraproject.org> - 20161108-2.gitb991c67
- Rebuilt for https://fedoraproject.org/wiki/Fedora_26_Mass_Rebuild

* Sun Dec 04 2016 Cole Robinson <crobinso@redhat.com> - 20161108-1.gitb991c67
- Rebase to version shipped with qemu 2.8

* Thu Feb 04 2016 Fedora Release Engineering <releng@fedoraproject.org> - 20150821-3.git4e03af8
- Rebuilt for https://fedoraproject.org/wiki/Fedora_24_Mass_Rebuild

* Tue Jan 26 2016 Cole Robinson <crobinso@redhat.com> 20150821-2.git4e03af8
- Build ipxe.efi (bug 1300865)
- Build eepro100 rom for qemu

* Tue Nov 17 2015 Cole Robinson <crobinso@redhat.com> - 20150821-1.git4e03af8
- Update to commit 4e03af8 for qemu 2.5
- Enable IPv6 (bug 1280318)

* Wed Jun 17 2015 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 20150407-3.gitdc795b9f
- Rebuilt for https://fedoraproject.org/wiki/Fedora_23_Mass_Rebuild

* Thu Apr 16 2015 Paolo Bonzini <pbonzini@redhat.com> - 20150407-2.gitdc795b9f
- Fix virtio bug with UEFI driver

* Thu Apr 16 2015 Paolo Bonzini <pbonzini@redhat.com> - 20150407-1.gitdc795b9f
- Update to latest upstream snapshot
- Switch source to .tar.xz
- Include patches from QEMU submodule
- Use config file for configuration
- Distribute additional permissions on top of GPLv2 ("UBDL")

* Sat Aug 16 2014 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 20140303-3.gitff1e7fc7
- Rebuilt for https://fedoraproject.org/wiki/Fedora_21_22_Mass_Rebuild

* Sat Jun 07 2014 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 20140303-2.gitff1e7fc7
- Rebuilt for https://fedoraproject.org/wiki/Fedora_21_Mass_Rebuild

* Mon Mar 03 2014 Cole Robinson <crobinso@redhat.com> - 20140303-1.gitff1e7fc7
- Allow access to ipxe prompt if VM is set to pxe boot (bz #842932)
- Enable PNG support (bz #1058176)

* Sat Aug 03 2013 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 20130517-3.gitc4bce43
- Rebuilt for https://fedoraproject.org/wiki/Fedora_20_Mass_Rebuild

* Mon May 20 2013 Paolo Bonzini <pbonzini@redhat.com> - 20130103-3.git717279a
- Fix BuildRequires, use cross-compiler when building on 32-bit i686
- Build UEFI drivers for QEMU and include them (patch from Gerd Hoffmann.
  BZ#958875)

* Fri May 17 2013 Daniel P. Berrange <berrange@redhat.com> - 20130517-1.gitc4bce43
- Update to latest upstream snapshot

* Fri May 17 2013 Daniel P. Berrange <berrange@redhat.com> - 20130103-3.git717279a
- Fix build with GCC 4.8 (rhbz #914091)

* Thu Feb 14 2013 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 20130103-2.git717279a
- Rebuilt for https://fedoraproject.org/wiki/Fedora_19_Mass_Rebuild

* Thu Jan  3 2013 Daniel P. Berrange <berrange@redhat.com> - 20130103-1.git717279a
- Updated to latest GIT snapshot

* Thu Jul 19 2012 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 20120328-2.gitaac9718
- Rebuilt for https://fedoraproject.org/wiki/Fedora_18_Mass_Rebuild

* Wed Mar 28 2012 Daniel P. Berrange <berrange@redhat.com> - 20120328-1.gitaac9718
- Update to newer upstream

* Fri Mar 23 2012 Daniel P. Berrange <berrange@redhat.com> - 20120319-3.git0b2c788
- Remove more defattr statements

* Tue Mar 20 2012 Daniel P. Berrange <berrange@redhat.com> - 20120319-2.git0b2c788
- Remove BuildRoot & rm -rf of it in install/clean sections
- Remove defattr in file section
- Switch to use global, instead of define for macros
- Add note about Patch1 not going upstream
- Split BRs across lines for easier readability

* Mon Feb 27 2012 Daniel P. Berrange <berrange@redhat.com> - 20120319-1.git0b2c788
- Initial package based on gPXE

* Fri Jan 13 2012 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 1.0.1-5
- Rebuilt for https://fedoraproject.org/wiki/Fedora_17_Mass_Rebuild

* Mon Feb 21 2011 Matt Domsch <mdomsch@fedoraproject.org> - 1.0.1-4
- don't use -Werror, it flags a failure that is not a failure for gPXE

* Mon Feb 21 2011 Matt Domsch <mdomsch@fedoraproject.org> - 1.0.1-3
- Fix virtio-net ethernet frame length (patch by cra), fixes BZ678789

* Tue Feb 08 2011 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 1.0.1-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_15_Mass_Rebuild

* Thu Aug  5 2010 Matt Domsch <mdomsch@fedoraproject.org> - 1.0.1-1
- New drivers: Intel e1000, e1000e, igb, EFI snpnet, JMicron jme,
  Neterion X3100, vxge, pcnet32.
- Bug fixes and improvements to drivers, wireless, DHCP, iSCSI,
  COMBOOT, and EFI.
* Tue Feb  2 2010 Matt Domsch <mdomsch@fedoraproject.org> - 1.0.0-1
- bugfix release, also adds wireless card support
- bnx2 builds again
- drop our one patch

* Tue Oct 27 2009 Matt Domsch <mdomsch@fedoraproject.org> - 0.9.9-1
- new upstream version 0.9.9
-- plus patches from git up to 20090818 which fix build errors and
   other release-critical bugs.
-- 0.9.9: added Attansic L1E and sis190/191 ethernet drivers.  Fixes
   and updates to e1000 and 3c90x drivers.
-- 0.9.8: new commands: time, sleep, md5sum, sha1sum. 802.11 wireless
   support with Realtek 8180/8185 and non-802.11n Atheros drivers.
   New Marvell Yukon-II gigabet Ethernet driver.  HTTP redirection
   support.  SYSLINUX floppy image type (.sdsk) with usable file
   system.  Rewrites, fixes, and updates to 3c90x, forcedeth, pcnet32,
   e1000, and hermon drivers.

* Mon Oct  5 2009 Matt Domsch <mdomsch@fedoraproject.org> - 0.9.7-6
- move rtl8029 from -roms to -roms-qemu for qemu ne2k_pci NIC (BZ 526776)

* Fri Jul 24 2009 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 0.9.7-5
- Rebuilt for https://fedoraproject.org/wiki/Fedora_12_Mass_Rebuild

* Tue May 19 2009 Matt Domsch <mdomsch@fedoraproject.org> - 0.9.7-4
- add undionly.kpxe to -bootimgs

* Tue May 12 2009 Matt Domsch <mdomsch@fedoraproject.org> - 0.9.7-3
- handle isolinux changing paths

* Sat May  9 2009 Matt Domsch <mdomsch@fedoraproject.org> - 0.9.7-2
- add dist tag

* Thu Mar 26 2009 Matt Domsch <mdomsch@fedoraproject.org> - 0.9.7-1
- Initial release based on etherboot spec
