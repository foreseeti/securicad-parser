# Release securiCAD parser

To make a release, perform the following steps:

1. Make a release commit and push it to a new branch
2. Make a pull request to `master` and get it approved and merged
3. Make a release tag for the merged pull request

### 1. Make a release commit and push it to a new branch
The release commit shall contain the following changes:

- Updated version number in `setup.cfg`
- Updated dependencies in `requirements.txt` and `dev-requirements.txt`

Test that everything still works with the new dependencies.

The name of the new branch doesn't matter, since it will be deleted after the release commit has been merged to `master`, but the convention for branch names is `<user-name>/<branch-name>`, e.g. `max/release`.

The commit message shall be `Release <version>`, e.g. `Release 0.0.2`.

```
$ git checkout -b max/release
$ sed -i 's/^version = .*$/version = 0.0.2/' setup.cfg
$ ./tools/scripts/create_requirements.sh
$ git add setup.cfg requirements.txt dev-requirements.txt
$ git commit -m "Release 0.0.2"
$ git push origin max/release
```

### 2. Make a pull request to `master` and get it approved and merged

Go to the repository on GitHub, click `Pull requests`, and then `New pull request`. Make sure that `base` is set to `master`, and set `compare` to your branch. Click `Create pull request`, add appropriate `Reviewers`, and add yourself as `Assignees`.

### 3. Make a release tag for the merged pull request

Once your pull request has been merged, you need to fetch the new merged commit in `master` to create the release tag:

```
$ git checkout master
$ git fetch
$ git merge --ff-only
$ git tag release/0.0.2
$ git push origin release/0.0.2
```
