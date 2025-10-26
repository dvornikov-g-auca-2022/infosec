#!/usr/bin/env bash

END_HOUR=18
END_MIN=0

now_epoch=$(date +%s)
end_today_epoch=$(date -d "today ${END_HOUR}:${END_MIN}" +%s)

if [ "$now_epoch" -ge "$end_today_epoch" ]; then
  echo "Current time: $(date +%H:%M). Work day has ended."
  exit 0
fi

remain=$((end_today_epoch - now_epoch))
hours=$((remain / 3600))
mins=$(((remain % 3600) / 60))

echo "Current time: $(date +%H:%M). Work day ends after ${hours} hours and ${mins} minutes."
