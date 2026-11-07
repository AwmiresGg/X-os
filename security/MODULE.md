# security

**Status:** Partial: ufw enabled deny-incoming in image; AppArmor added to package list

**Dependencies:** ufw, apparmor, polkit

**Tests:** boot self-test checks firewall active

**Known issues / limitations:**
- Security Center UI, polkit policies for X-OS helpers not started.

**Acceptance criteria:**
- [ ] Firewall on by default
- [ ] No services listening by default
- [ ] Signed packages only

**Documentation:** see `architecture/ARCHITECTURE.md` and `documentation/`.
