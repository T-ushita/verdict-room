#!/usr/bin/env bash
# Records read-only GitHub responses into fixtures/.
# Filename convention: path without query string, "/" replaced with "__".
set -eu

if [[ -z "${GITHUB_TOKEN:-}" ]]; then
  echo "GITHUB_TOKEN (read-only) is required" >&2
  exit 1
fi

repo="${VERDICT_REPO:-sandbox-quantum/switch}"
issues="${1:-820 825}"
mkdir -p fixtures

save() {
  local path="$1"
  local output="${2:-}"
  local filename
  if [[ -n "${output}" ]]; then
    filename="${output}"
  else
    filename="${path#/}"
    filename="${filename%%\?*}"
    filename="${filename//\//__}.json"
  fi
  curl --fail --silent --show-error \
    -H "Accept: application/vnd.github+json" \
    -H "Authorization: Bearer ${GITHUB_TOKEN}" \
    "https://api.github.com/${path#/}" \
    > "fixtures/${filename}"
}

for issue in ${issues}; do
  save "repos/${repo}/issues/${issue}"
  save "search/issues?q=repo:${repo}+is:pr+%23${issue}+in:title,body" \
    "search__issues__${issue}.json"
  search_file="fixtures/search__issues__${issue}.json"
  while IFS= read -r pr; do
    pr_path="repos/${repo}/pulls/${pr}"
    pr_file="${pr_path//\//__}.json"
    save "${pr_path}"
    save "${pr_path}/files?per_page=100"
    sha="$(python3 -c "import json; print(json.load(open('fixtures/${pr_file}'))['head']['sha'])")"
    save "repos/${repo}/commits/${sha}/check-runs"
  done < <(python3 -c "import json; print('\n'.join(str(x['number']) for x in json.load(open('${search_file}'))['items']))")
done
