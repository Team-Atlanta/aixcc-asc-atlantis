/* eslint-disable camelcase */
import { inspect } from 'util'

// packages
import { Octokit } from "@octokit/action";

const [owner, sandbox_repo] = process.env.GITHUB_REPOSITORY.split("/");

async function repos(octokit) {
  // construct this template repo full name
  const full_name = `${owner}/${sandbox_repo}`;

  // determine type
  const {
    data: {
      is_template,
      owner: { type },
    },
  } = await octokit.request("GET /repos/{owner}/{repo}", {
    owner,
    repo: sandbox_repo,
  });

  // exit early
  if (!is_template) {
    console.log("action executed on non template repository");
    process.exit(0);
  }

  const api = type === "User" ? "GET /user/repos" : "GET /orgs/{org}/repos";

  const all = await octokit.paginate(api, {
    username: owner,
    org: owner,
    per_page: 100,
    affiliation: "owner",
  });

  const repositories = all.filter((repo) => repo.archived === false); // only include non-archived repos

  console.log(
    `repo owner type is "${type}" with ${repositories.length} repositories`
  );


  // find all repos that depend on this template
  let dependents = repositories
    .filter(
      (repo) =>
        repo.name.startsWith("asc-crs-")
    )
    .map((repo) => repo.name);

  console.log(`found ${dependents.length} repositories marked as dependents`);


  return dependents;
}

function delay(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

async function dispatchEventToRepo(repo) {
  console.log(`🔄 syncing repository "${repo}"`);
  await octokit.request("POST /repos/{owner}/{repo}/dispatches", {
    owner,
    repo,
    event_type: "trigger-template-sync",
  });
}

const octokit = new Octokit();
const repositories = await repos(octokit);

// exit early: no repos to update
if (repositories.length === 0) {
  console.log("✅ no repositories to update");
  process.exit(0);
}

for (const repo of repositories) {
  // Just sends dispatch event. Sync action will add delay to prevent API rate-limiting
  await dispatchEventToRepo(repo);
  await delay(1000);
}