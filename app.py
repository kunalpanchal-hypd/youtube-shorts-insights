import streamlit as st
import pandas as pd
from googleapiclient.discovery import build
import re


st.set_page_config(
    page_title="YouTube Shorts Insights",
    page_icon="▶️",
    layout="wide"
)

st.title("▶️ YouTube Shorts Insights")
st.write("Upload a CSV containing YouTube Shorts links to get video insights.")


# Get YouTube API key from Streamlit secrets
API_KEY = st.secrets["YOUTUBE_API_KEY"]


def extract_video_id(url):
    """Extract a YouTube video ID from common YouTube URL formats."""

    if not isinstance(url, str):
        return None

    patterns = [
        r"(?:youtube\.com/shorts/)([A-Za-z0-9_-]{11})",
        r"(?:youtube\.com/watch\?v=)([A-Za-z0-9_-]{11})",
        r"(?:youtu\.be/)([A-Za-z0-9_-]{11})",
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)

    return None

def get_video_data(video_ids):
    """Fetch video information from YouTube Data API."""

    youtube = build("youtube", "v3", developerKey=API_KEY)

    results = []

    # YouTube allows up to 50 video IDs per API request
    for i in range(0, len(video_ids), 50):
        batch = video_ids[i:i + 50]

        response = youtube.videos().list(
            part="snippet,statistics",
            id=",".join(batch)
        ).execute()

        # Store the videos YouTube actually returned
        returned_videos = {}

        for video in response.get("items", []):
            returned_videos[video["id"]] = video

        # Get unique channel IDs from this batch
        channel_ids = []

        for video in returned_videos.values():
            channel_id = video.get("snippet", {}).get("channelId", "")

            if channel_id and channel_id not in channel_ids:
                channel_ids.append(channel_id)

        # Fetch channel information in batches
        channel_data = {}

        for j in range(0, len(channel_ids), 50):
            channel_batch = channel_ids[j:j + 50]

            channel_response = youtube.channels().list(
                part="snippet,statistics",
                id=",".join(channel_batch)
            ).execute()

            for channel in channel_response.get("items", []):
                channel_data[channel["id"]] = channel

        # Create a result for every requested video ID
        for video_id in batch:

            if video_id not in returned_videos:
                results.append({
                    "Video ID": video_id,
                    "Title": "",
                    "Views": "",
                    "Likes": "",
                    "Comments": "",
                    "Tags": "",
                    "Channel Name": "",
                    "Total Videos": "",
                    "Total Views": "",
                    "Total Subscribers": "",
                    "Average Views": "",
                    "Status": "Not found / unavailable"
                })
                continue

            video = returned_videos[video_id]

            snippet = video.get("snippet", {})
            statistics = video.get("statistics", {})

            channel_id = snippet.get("channelId", "")
            channel = channel_data.get(channel_id, {})

            channel_name = channel.get(
                "snippet", {}
            ).get("title", "")

            channel_statistics = channel.get(
                "statistics", {}
            )

            total_videos = int(
                channel_statistics.get("videoCount", 0)
            )

            total_views = int(
                channel_statistics.get("viewCount", 0)
            )

            total_subscribers = int(
                channel_statistics.get("subscriberCount", 0)
            )

            average_views = (
                total_views / total_videos
                if total_videos > 0
                else 0
            )

            title = snippet.get("title", "")
            description = snippet.get("description", "")

            text_to_search = f"{title} {description}"

            tags_and_mentions = re.findall(
                r"(?:#|@)[A-Za-z0-9_]+",
                text_to_search
            )

            # Remove duplicates while preserving order
            tags_and_mentions = list(
                dict.fromkeys(tags_and_mentions)
            )

            tags = ", ".join(tags_and_mentions)

            results.append({
                "Video ID": video["id"],
                "Title": title,
                "Views": int(
                    statistics.get("viewCount", 0)
                ),
                "Likes": int(
                    statistics.get("likeCount", 0)
                ),
                "Comments": int(
                    statistics.get("commentCount", 0)
                ),
                "Tags": tags,
                "Channel Name": channel_name,
                "Total Videos": total_videos,
                "Total Views": total_views,
                "Total Subscribers": total_subscribers,
                "Average Views": round(
                    average_views, 2
                ),
                "Status": "Found"
            })

    return results
uploaded_file = st.file_uploader(
    "Upload your CSV file",
    type=["csv"]
)


if uploaded_file is not None:

    try:
        df = pd.read_csv(uploaded_file)

        st.success(f"CSV loaded successfully. Found {len(df)} rows.")

        st.subheader("Your CSV")

        st.dataframe(df, use_container_width=True)

        if len(df.columns) == 0:
            st.error("The CSV does not contain any columns.")

        else:
            column = st.selectbox(
                "Select the column containing YouTube links:",
                df.columns
            )

            if st.button("Get YouTube Insights"):

                with st.spinner("Extracting video information..."):

                    video_ids = []
                    url_by_video_id = {}

                    for url in df[column]:
                        video_id = extract_video_id(url)

                        if video_id:
                            video_ids.append(video_id)
                            url_by_video_id[video_id] = url

                    # Remove duplicate video IDs while preserving order
                    video_ids = list(dict.fromkeys(video_ids))

                    if not video_ids:
                        st.error(
                            "No valid YouTube video links were found in the selected column."
                        )

                    else:
                        st.info(
                            f"Found {len(video_ids)} valid YouTube video IDs."
                        )

                        try:
                            results = get_video_data(video_ids)

                            if results:
                                results_df = pd.DataFrame(results)

                                results_df.insert(
                                    0,
                                    "URL",
                                    results_df["Video ID"].map(url_by_video_id)
                                )

                                st.subheader("YouTube Insights")

                                st.dataframe(
                                    results_df,
                                    use_container_width=True
                                )

                                csv = results_df.to_csv(index=False)

                                st.download_button(
                                    label="Download Results as CSV",
                                    data=csv,
                                    file_name="youtube_shorts_insights.csv",
                                    mime="text/csv"
                                )

                            else:
                                st.warning(
                                    "No video information was returned by YouTube."
                                )

                        except Exception as e:
                            st.error(
                                f"Something went wrong while contacting YouTube: {e}"
                            )

    except Exception as e:
        st.error(f"Could not read the CSV file: {e}")