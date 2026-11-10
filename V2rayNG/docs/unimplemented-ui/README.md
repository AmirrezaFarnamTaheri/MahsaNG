# Unimplemented MASQUE/WARP editor layouts — preserved for source restoration

These four XML layouts were checked into the public MahsaNG tree, but their declared
Activity classes (`.feature.masqueGenerator.AddMasqueActivity` and
`.feature.warpGenerator.AddWarpActivity`) **are absent**, as are their companion
styles, drawables, strings, and field validation/persistence logic.

They are preserved **byte-for-byte** in this directory, outside Android's
`src/main/res` folder. The archived resources are not compiled or presented
to users, so they cannot pretend to provide a working key-generation feature.

The original upstream source added the app layouts in
[GFW-knocker/MahsaNG commit b049f70](https://github.com/GFW-knocker/MahsaNG/commit/b049f70296b95ee8d4e9e1af7f6f0e368aa98902)
without the referenced supporting resources.

### Restore only when the feature is real
1. Obtain/author reviewed MASQUE/WARP Activity, input validation, secure
   key handling and protocol integration, with verified licensing and source.
2. Restore **both** portrait and television layout files plus all referenced
   string, drawable and color resources with accessibility and Persian RTL QA.
3. Register the activities and test both the generated profile and actual
   tunneled connection in an instrumented Android device build.
4. Remove the archive guard after the replacement feature and resources
   have been verified.

This quarantine is not a substitute for implementation and does not disable
any working Activity in the public source because neither Activity exists.
