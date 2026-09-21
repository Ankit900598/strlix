package com.zevi.agent;

import android.view.Gravity;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.FrameLayout;
import android.widget.TextView;

import androidx.annotation.NonNull;
import androidx.recyclerview.widget.RecyclerView;

import java.util.ArrayList;
import java.util.List;

public class MessageAdapter extends RecyclerView.Adapter<MessageAdapter.VH> {
    public static class Message {
        final boolean fromUser;
        final String text;

        Message(boolean fromUser, String text) {
            this.fromUser = fromUser;
            this.text = text;
        }

        static Message user(String t) {
            return new Message(true, t);
        }

        static Message agent(String t) {
            return new Message(false, t);
        }
    }

    private final List<Message> items = new ArrayList<>();

    public void add(Message m) {
        items.add(m);
        notifyItemInserted(items.size() - 1);
    }

    @NonNull
    @Override
    public VH onCreateViewHolder(@NonNull ViewGroup parent, int viewType) {
        View v = LayoutInflater.from(parent.getContext()).inflate(R.layout.item_message, parent, false);
        return new VH(v);
    }

    @Override
    public void onBindViewHolder(@NonNull VH holder, int position) {
        Message m = items.get(position);
        holder.text.setText(m.text);
        holder.text.setContentDescription(m.fromUser
                ? parentLabel(holder, m.text, true)
                : parentLabel(holder, m.text, false));
        FrameLayout.LayoutParams lp = (FrameLayout.LayoutParams) holder.text.getLayoutParams();
        if (m.fromUser) {
            lp.gravity = Gravity.END;
            holder.text.setBackgroundResource(R.drawable.bg_user_msg);
        } else {
            lp.gravity = Gravity.START;
            holder.text.setBackgroundResource(R.drawable.bg_agent_msg);
        }
        holder.text.setLayoutParams(lp);
    }

    private String parentLabel(@NonNull VH holder, String text, boolean user) {
        return holder.itemView.getContext().getString(
                user ? R.string.message_you : R.string.message_strlix, text);
    }

    @Override
    public int getItemCount() {
        return items.size();
    }

    static class VH extends RecyclerView.ViewHolder {
        final TextView text;

        VH(@NonNull View itemView) {
            super(itemView);
            text = itemView.findViewById(R.id.messageText);
        }
    }
}
