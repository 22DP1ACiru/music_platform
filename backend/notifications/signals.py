from django.db.models.signals import post_save
from django.dispatch import receiver
from django.urls import reverse # For constructing links if needed
from interactions.models import Follow
from music.models import Release
from shop.models import Order, OrderItem # If Order completion creates notifications
from chat.models import Message as ChatMessage, Conversation
from .models import Notification
import logging

logger = logging.getLogger(__name__)

@receiver(post_save, sender=Follow)
def create_follow_notification(sender, instance: Follow, created: bool, **kwargs):
    if created:
        artist_owner = instance.artist.user
        if artist_owner != instance.user: # Don't notify if someone follows their own artist profile (should not happen)
            Notification.objects.create(
                recipient=artist_owner,
                actor_user=instance.user,
                verb=f"started following you",
                description=f"{instance.user.username} is now following your artist profile: {instance.artist.name}.",
                notification_type=Notification.NotificationType.NEW_FOLLOWER,
                target_artist_profile=instance.artist,
                target_user_profile=instance.user,
                is_artist_channel=True
            )
            logger.info(f"Created NEW_FOLLOWER notification for {artist_owner.username} from {instance.user.username} for artist {instance.artist.name}")


@receiver(post_save, sender=Release)
def create_new_release_notifications(sender, instance: Release, created: bool, **kwargs):
    # Notify followers only if the release is newly published or an existing draft is published
    # And ensure it's not a future release date.
    # This logic might be complex if is_published can be toggled.
    # A simpler approach: if created and is_published and release_date is not future.
    # Or if updated from not is_published to is_published.
    
    is_newly_effectively_published = False
    if created and instance.is_visible():
        is_newly_effectively_published = True
    elif not created: # It's an update
        try:
            old_instance = Release.objects.get(pk=instance.pk)
            if not old_instance.is_visible() and instance.is_visible():
                is_newly_effectively_published = True
        except Release.DoesNotExist:
            pass # Should not happen in post_save for existing

    if is_newly_effectively_published:
        followers = Follow.objects.filter(artist=instance.artist).select_related('user')
        for follow_relation in followers:
            Notification.objects.create(
                recipient=follow_relation.user,
                actor_artist=instance.artist,
                verb=f"released a new {instance.get_release_type_display().lower()}",
                description=f"{instance.artist.name} just released: {instance.title}",
                notification_type=Notification.NotificationType.NEW_RELEASE,
                target_release=instance,
                target_artist_profile=instance.artist,
                is_artist_channel=False # This is for the user's feed
            )
        logger.info(f"Created NEW_RELEASE notifications for followers of {instance.artist.name} for release {instance.title}")


@receiver(post_save, sender=Order)
def create_sale_notification_for_artist(sender, instance: Order, created: bool, **kwargs):
    if instance.status == Order.ORDER_STATUS_CHOICES[2][0]: # COMPLETED
        # Check if this is a newly completed order
        try:
            old_instance = Order.objects.get(pk=instance.pk)
            if old_instance.status != Order.ORDER_STATUS_CHOICES[2][0]: # Was not completed before
                is_newly_completed = True
            else:
                is_newly_completed = False # Already completed, no new notification
        except Order.DoesNotExist: # This means it's a new order directly created as COMPLETED (less likely)
            is_newly_completed = True
        
        if is_newly_completed:
            order_items = instance.items.select_related('product__release__artist__user').all()
            notified_artists = set() # To avoid multiple notifications for the same artist if they have multiple items in order
            
            for item in order_items:
                if item.product.release and item.product.release.artist:
                    artist_profile = item.product.release.artist
                    artist_owner = artist_profile.user
                    
                    if artist_owner and artist_owner.id not in notified_artists:
                        # If a user buys their own release, do not notify them as an artist.
                        if instance.user and instance.user == artist_owner:
                            continue

                        Notification.objects.create(
                            recipient=artist_owner,
                            actor_user=instance.user, # The user who made the purchase
                            verb=f"made a sale!",
                            description=f"{instance.user.username if instance.user else 'A user'} purchased '{item.product.name}'. Order total: {instance.total_amount} {instance.currency}",
                            notification_type=Notification.NotificationType.SALE_MADE_ARTIST,
                            target_order=instance,
                            target_release=item.product.release, # Link to the specific release sold
                            target_artist_profile=artist_profile, # The artist whose item was sold
                            is_artist_channel=True
                        )
                        notified_artists.add(artist_owner.id)
                        logger.info(f"Created SALE_MADE_ARTIST notification for artist {artist_profile.name} regarding order {instance.id}")


@receiver(post_save, sender=ChatMessage)
def create_chat_message_notification(sender, instance: ChatMessage, created: bool, **kwargs):
    if created:
        conversation = instance.conversation
        sender_user = instance.sender_user # The actual user account sending the message

        for participant_user in conversation.participants.all():
            if participant_user != sender_user: # Don't notify the sender
                # Determine if this notification is for the recipient's User channel or Artist channel
                is_for_artist_channel = False
                recipient_as_artist = None

                # Case 1: Conversation was initiated by someone else TO this participant's artist profile
                if conversation.related_artist_recipient and \
                   hasattr(participant_user, 'artist_profile') and \
                   participant_user.artist_profile == conversation.related_artist_recipient:
                    is_for_artist_channel = True
                    recipient_as_artist = participant_user.artist_profile
                
                # Case 2: Conversation was initiated by this participant AS an artist profile
                # (and the message is from the other party)
                elif conversation.initiator_user == participant_user and \
                     conversation.initiator_identity_type == Conversation.IdentityType.ARTIST and \
                     conversation.initiator_artist_profile:
                    is_for_artist_channel = True
                    recipient_as_artist = conversation.initiator_artist_profile

                message_sender_display = instance.sender_user.username
                if instance.sender_identity_type == ChatMessage.SenderIdentity.ARTIST and instance.sending_artist:
                    message_sender_display = f"{instance.sending_artist.name} (Artist)"

                Notification.objects.create(
                    recipient=participant_user,
                    actor_user=sender_user, # User who sent the message
                    actor_artist=instance.sending_artist if instance.sender_identity_type == ChatMessage.SenderIdentity.ARTIST else None,
                    verb=f"sent you a new message",
                    description=f"{message_sender_display}: {instance.text[:50] if instance.text else '[Attachment]'}",
                    notification_type=Notification.NotificationType.NEW_CHAT_MESSAGE,
                    target_conversation=conversation,
                    is_artist_channel=is_for_artist_channel,
                    target_artist_profile=recipient_as_artist if is_for_artist_channel else None 
                )
                logger.info(f"Created NEW_CHAT_MESSAGE notification for {participant_user.username} from {message_sender_display} in conv {conversation.id}")