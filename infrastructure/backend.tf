# backend.tf
terraform {
  backend "gcs" {
    bucket = "tfstate-gen-lang-client-0220328793-1781177452"   # use the actual bucket name from step 1
    prefix = "terraform/state"
  }
}