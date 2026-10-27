# Quality Criteria — What to Judge the Product Against

Use this when deciding what you want to test the whole product, individual features or particular product aspects against. Each category below is a quality aspect to test. Not every category matters equally for every product. Depending on the user engagement mode either ask the user to tell you what’s important for the product, or judge yourself based on what you know about the product type, domain and users.

## Capability — can it do what's required based on provided requirements?
- Sufficiency: does it have all the capabilities it needs to serve its purpose?
- Correctness: does it function as intended and produce acceptable output?

## Reliability — does it keep working, and fail well when it doesn't?
- [#IGNORE] Robustness: does it keep functioning over time without degrading?
- Error handling: does it resist bad data, fail gracefully, and recover?
- Data integrity: is data protected from loss or corruption?
- Safety: could a failure cause harm to people or property?

## Usability — how easy is it for a real user?
- [#IGNORE] Learnability: can the intended user pick it up quickly?
- [#IGNORE] Operability: can it be operated with minimal effort/friction?
- Accessibility: does it meet accessibility standards and work with OS accessibility features?

## [#IGNORE] Charisma — how appealing is it?
- [#IGNORE] Aesthetics: does it appeal to the senses?
- [#IGNORE] Uniqueness: does it offer something new or distinct?
- [#IGNORE] Entrancement: do users get engaged, hooked, enjoy using it?
- [#IGNORE] Image: does it project the intended impression of quality?

## Security — how well is it protected?
- Authentication: how does it verify who a user is?
- Authorization: what rights do authenticated users get at each privilege level?
- Privacy: how is customer/employee data protected from unauthorized access?
- Security holes: where could enforcement fail (including social-engineering angles)?

## Scalability — how well does it scale up or down?

## Compatibility — how well does it work with the outside world?
- Application compatibility: works alongside other software
- OS compatibility: works with the target operating system(s)
- Hardware compatibility: works with target hardware
- Backward compatibility: works with earlier versions of itself
- Footprint: doesn't unnecessarily consume memory/storage/other resources

## Performance — how fast and responsive is it?

## Installability — how easily can it be installed?
- System requirements: does it detect missing/insufficient components?
- Configuration: what's affected by install, where are files/resources stored?
- Uninstallation: does it clean up completely when removed?
- Upgrades/patches: can new versions be added while respecting existing config?
- Administration: does install require special personnel/scheduling?

## How to use this list

- Ignore categories and quality criteria with the #IGNORE tag. Do not collect information about it. Do not test it.
- When scoping or generating charters, reason yourself which of these criteria matter most for *this* test engagement. Rely on your knowledge of the product under test, and your knowledge of the particular changes that are to be tested.
- If the user specified explicitly what quality criteria to test, focus on them only. Do not get distructed on other criteria.
- For each category chosen for testing, defin how would you approach the testing.


