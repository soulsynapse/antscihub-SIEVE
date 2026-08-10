---
title: A bump adds, and a removal is paid at the version
adr: 38
position: "02.06"
status: settled
decided: 2026-08-10
---

A schema bump adds fields and never repurposes one, a bump that removes one is
paid in full at that version, and a load keeps the version it read.

The reader refuses a document from the future and never restamps one from the
past, so the stamp says what the document declares and rises only when a build
writes into it something the declared version does not have. The price of a
removal is that the field is gone: `extra="forbid"` refuses every document still
carrying it by name, and none of them opens again.

Why: v2's record is the case for additive. Five schema versions in thirteen
days, four purely additive, and no transform code was ever written — a migration
layer would have been apparatus for a shape the work did not take. Repurposing
is the one change excluded outright rather than priced, because it is the only
one no reader can detect: a field that keeps its name and changes its meaning
loads clean and runs something else.

Against the restamp this replaces, whose own argument was that a document this
build accepted *is* a document in this build's schema: that holds of what the
build read and not of what the file says, and the two are the same document
until a front end saves. A GUI saves by copying the `Project` it opened, so a
restamp relabels every file merely opened by a newer build, and the build that
wrote it then refuses its own project by a version number rather than by
anything a user did. Keeping the stamp costs the property the restamp was
bought for — a stamp is no longer proof that the file has been through this
build's validator — and that property was never worth a silent edit to someone
else's file.

The removal clause is what
[a-document-names-footage-only-through-a-tool](a-document-names-footage-only-through-a-tool.md)
needs and does not have; its "the cost is charged once, at the version" is this
paragraph's direction. Forbidding removal outright would reopen that decision,
and it is not the removal that is expensive — it is the documents in the wild
that carry the field. There are none, which is what makes the price zero today
and is the whole of why the removal is affordable now and would not be later.
After a project exists that a user cannot re-create, the same bump costs an
importer, and [v2-does-not-import](v2-does-not-import.md) is the standing
judgment on what one of those is worth.
