use std::{error::Error, fs, sync::Arc};
/*
use twilight_cache_inmemory::{DefaultInMemoryCache, ResourceType};
use twilight_gateway::{Event, EventTypeFlags, Intents, Shard, ShardId, StreamExt as _};
use twilight_http::Client as HttpClient;
*/

// #[tokio::main]
fn main() -> Result<(), std::io::Error> {
    let token = fs::read_to_string("../token.txt")?;
    println!("Nazareth's token: {}", token);
    Ok(())
}
